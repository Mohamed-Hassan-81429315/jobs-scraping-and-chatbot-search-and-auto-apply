<?php

namespace App\Http\Controllers;

use App\Models\User;
use App\Services\CvParser;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;
use Illuminate\Validation\ValidationException;
use Symfony\Component\HttpFoundation\StreamedResponse;

class ProfileController extends Controller
{
    private const DISK = 'local'; // private: files are served only through the endpoints below

    public function show(Request $request): JsonResponse
    {
        return response()->json(['profile' => $this->payload($request->user())]);
    }

    public function update(Request $request): JsonResponse
    {
        $number = $request->input('national_number');
        if (is_string($number)) {
            $request->merge(['national_number' => strtoupper(preg_replace('/[\s\-]+/', '', $number))]);
        }

        $data = $request->validate([
            'name' => ['sometimes', 'required', 'string', 'max:80'],
            'phone' => ['nullable', 'string', 'max:32', 'regex:/^\+?[0-9 ()\-]{6,32}$/'],
            'headline' => ['nullable', 'string', 'max:120'],
            'location' => ['nullable', 'string', 'max:120'],
            'summary' => ['nullable', 'string', 'max:2000'],
            'skills' => ['nullable', 'array', 'max:50'],
            'skills.*' => ['string', 'max:40'],
            'birth_date' => ['nullable', 'date_format:Y-m-d', 'after:1899-12-31', 'before:today'],
            'national_number' => ['nullable', 'string', 'regex:/^[A-Z0-9]{6,20}$/'],
            'clear_national_number' => ['nullable', 'boolean'],
        ], [
            'phone.regex' => 'Enter a valid phone number.',
            'national_number.regex' => 'Use 6 to 20 letters or digits, without symbols.',
        ]);

        $user = $request->user();
        $fill = [];

        foreach (['name', 'phone', 'headline', 'location', 'summary'] as $field) {
            if (array_key_exists($field, $data)) {
                $value = is_string($data[$field]) ? trim($data[$field]) : $data[$field];
                $fill[$field] = $value === '' ? null : $value;
            }
        }
        if (array_key_exists('skills', $data)) {
            $skills = collect($data['skills'] ?? [])->map(fn ($s) => trim($s))->filter()->unique(fn ($s) => mb_strtolower($s))->values()->all();
            $fill['skills'] = $skills ?: null;
        }

        $birth = array_key_exists('birth_date', $data) ? ($data['birth_date'] ?: null) : $user->birth_date?->format('Y-m-d');

        if (!empty($data['clear_national_number'])) {
            $fill['national_number'] = null;
        } elseif (!empty($data['national_number'])) {
            $number = $data['national_number'];
            if (preg_match('/^\d{14}$/', $number)) {
                $derived = CvParser::birthFromNationalNumber($number);
                if (!$derived) {
                    throw ValidationException::withMessages(['national_number' => ['This is not a valid 14-digit national number.']]);
                }
                if ($birth && $birth !== $derived) {
                    throw ValidationException::withMessages(['birth_date' => ['The birth date does not match the national number.']]);
                }
                $birth ??= $derived;
            }
            $fill['national_number'] = $number;
        }

        if (array_key_exists('birth_date', $data) || ($fill['national_number'] ?? null)) {
            $fill['birth_date'] = $birth;
        }

        $user->forceFill($fill)->save();

        return response()->json(['profile' => $this->payload($user->fresh())]);
    }

    /** Only way to read the full number: an explicit, throttled request (the page masks it). */
    public function nationalNumber(Request $request): JsonResponse
    {
        return response()->json(['national_number' => $request->user()->national_number]);
    }

    public function uploadPhoto(Request $request): JsonResponse
    {
        $request->validate(['photo' => ['required', 'file', 'mimes:jpg,jpeg,png,webp', 'max:3072']], [
            'photo.max' => 'The photo must be 3 MB or smaller.',
            'photo.uploaded' => 'The upload failed. If the photo is under 3 MB, raise upload_max_filesize in php.ini (see the install notes).',
            'photo.mimes' => 'Use a JPG, PNG or WebP image.',
        ]);

        $user = $request->user();
        $file = $request->file('photo');
        $bytes = $this->squareJpeg((string) file_get_contents($file->getRealPath()));
        $ext = $bytes['jpeg'] ? 'jpg' : strtolower($file->extension() ?: 'jpg');

        $path = "profiles/{$user->id}/photo-" . Str::random(16) . '.' . $ext;
        Storage::disk(self::DISK)->put($path, $bytes['data']);
        $this->forget($user->photo_path);
        $user->forceFill(['photo_path' => $path])->save();

        return response()->json(['profile' => $this->payload($user->fresh())]);
    }

    public function deletePhoto(Request $request): JsonResponse
    {
        $user = $request->user();
        $this->forget($user->photo_path);
        $user->forceFill(['photo_path' => null])->save();

        return response()->json(['profile' => $this->payload($user->fresh())]);
    }

    public function photo(Request $request)
    {
        $path = $request->user()->photo_path;
        if (!$path || !Storage::disk(self::DISK)->exists($path)) {
            abort(404);
        }

        return Storage::disk(self::DISK)->response($path, null, [
            'Cache-Control' => 'private, max-age=300',
            'X-Content-Type-Options' => 'nosniff',
        ]);
    }

    public function uploadCv(Request $request): JsonResponse
    {
        $request->validate(['cv' => ['required', 'file', 'mimes:pdf,docx', 'max:5120']], [
            'cv.max' => 'The CV must be 5 MB or smaller.',
            'cv.uploaded' => 'The upload failed. If the CV is under 5 MB, raise upload_max_filesize in php.ini (see the install notes).',
            'cv.mimes' => 'Upload your CV as a PDF or DOCX file.',
        ]);

        $user = $request->user();
        $file = $request->file('cv');
        $ext = strtolower($file->getClientOriginalExtension());
        $head = (string) file_get_contents($file->getRealPath(), false, null, 0, 4);

        // The extension and the content must agree (PDF starts "%PDF", DOCX is a zip: "PK").
        if (($ext === 'pdf' && $head !== '%PDF') || ($ext === 'docx' && !str_starts_with($head, 'PK'))) {
            throw ValidationException::withMessages(['cv' => ['This file is not a valid ' . strtoupper($ext) . ' document.']]);
        }

        $name = trim(preg_replace('/[^\p{L}\p{N}._\- ()]+/u', '', basename($file->getClientOriginalName()))) ?: "cv.$ext";
        $path = "profiles/{$user->id}/cv-" . Str::random(16) . '.' . $ext;
        Storage::disk(self::DISK)->putFileAs("profiles/{$user->id}", $file, basename($path));

        $this->forget($user->cv_path);
        $user->forceFill([
            'cv_path' => $path,
            'cv_name' => mb_substr($name, 0, 150),
            'cv_uploaded_at' => now(),
        ])->save();

        return response()->json([
            'profile' => $this->payload($user->fresh()),
            'autofill' => $this->suggestions($user->fresh()),
        ], 201);
    }

    /** Re-read the saved CV and return guesses. Nothing is saved: the user reviews them first. */
    public function autofill(Request $request): JsonResponse
    {
        if (!$request->user()->cv_path) {
            throw ValidationException::withMessages(['cv' => ['Upload your CV first.']]);
        }

        return response()->json(['autofill' => $this->suggestions($request->user())]);
    }

    public function downloadCv(Request $request): StreamedResponse
    {
        $user = $request->user();
        if (!$user->cv_path || !Storage::disk(self::DISK)->exists($user->cv_path)) {
            abort(404);
        }

        return Storage::disk(self::DISK)->download($user->cv_path, $user->cv_name ?: basename($user->cv_path), [
            'X-Content-Type-Options' => 'nosniff',
        ]);
    }

    public function deleteCv(Request $request): JsonResponse
    {
        $user = $request->user();
        $this->forget($user->cv_path);
        $user->forceFill(['cv_path' => null, 'cv_name' => null, 'cv_uploaded_at' => null])->save();

        return response()->json(['profile' => $this->payload($user->fresh())]);
    }

    private function suggestions(User $user): array
    {
        $disk = Storage::disk(self::DISK);
        $parser = new CvParser();
        $text = $parser->extractText($disk->path($user->cv_path), pathinfo($user->cv_path, PATHINFO_EXTENSION));

        if (trim($text) === '') {
            return ['readable' => false, 'fields' => (object) []];
        }

        $found = $parser->parse($text);
        unset($found['email']); // the email is the login; never changed from a CV

        return [
            'readable' => true,
            'fields' => array_filter($found, fn ($v) => $v !== null && $v !== '' && $v !== []),
        ];
    }

    private function payload(User $user): array
    {
        $number = $user->national_number;

        return [
            'id' => $user->id,
            'name' => $user->name,
            'email' => $user->email,
            'phone' => $user->phone,
            'headline' => $user->headline,
            'location' => $user->location,
            'summary' => $user->summary,
            'skills' => $user->skills ?? [],
            'birth_date' => $user->birth_date?->format('Y-m-d'),
            'has_national_number' => (bool) $number,
            'national_number_masked' => $number ? str_repeat('•', max(strlen($number) - 4, 0)) . substr($number, -4) : null,
            'has_photo' => (bool) $user->photo_path,
            'photo_version' => $user->photo_path ? substr(md5($user->photo_path), 0, 8) : null,
            'has_cv' => (bool) $user->cv_path,
            'cv_name' => $user->cv_name,
            'cv_uploaded_at' => $user->cv_uploaded_at?->toIso8601String(),
        ];
    }

    private function forget(?string $path): void
    {
        if ($path && Storage::disk(self::DISK)->exists($path)) {
            Storage::disk(self::DISK)->delete($path);
        }
    }

    /** Centre-crop to a 512px square JPEG (also strips EXIF/GPS). Falls back to the original bytes without GD. */
    private function squareJpeg(string $bytes): array
    {
        if (!function_exists('imagecreatefromstring')) {
            return ['data' => $bytes, 'jpeg' => false];
        }
        $src = @imagecreatefromstring($bytes);
        if (!$src) {
            throw ValidationException::withMessages(['photo' => ['This image could not be read.']]);
        }
        $w = imagesx($src);
        $h = imagesy($src);
        $side = min($w, $h);
        $dst = imagecreatetruecolor(512, 512);
        imagefill($dst, 0, 0, imagecolorallocate($dst, 255, 255, 255));
        imagecopyresampled($dst, $src, 0, 0, intdiv($w - $side, 2), intdiv($h - $side, 2), 512, 512, $side, $side);

        ob_start();
        imagejpeg($dst, null, 86);
        $data = (string) ob_get_clean();

        return ['data' => $data, 'jpeg' => true];
    }
}
