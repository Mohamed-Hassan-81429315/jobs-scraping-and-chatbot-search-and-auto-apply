<?php

namespace Tests\Feature;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Storage;
use Laravel\Sanctum\Sanctum;
use Tests\TestCase;
use ZipArchive;

class ProfileTest extends TestCase
{
    use RefreshDatabase;

    private function login(): User
    {
        Storage::fake('local');
        $user = User::factory()->create(['email' => 'sara@example.com']);
        Sanctum::actingAs($user);

        return $user;
    }

    private function docx(string $text): UploadedFile
    {
        $path = tempnam(sys_get_temp_dir(), 'cv') . '.docx';
        $zip = new ZipArchive();
        $zip->open($path, ZipArchive::CREATE);
        $zip->addFromString('word/document.xml', '<w:document><w:body>' . implode('', array_map(
            fn ($l) => '<w:p><w:r><w:t>' . htmlspecialchars($l) . '</w:t></w:r></w:p>',
            explode("\n", $text)
        )) . '</w:body></w:document>');
        $zip->close();

        return new UploadedFile($path, 'My CV.docx', null, null, true);
    }

    public function test_guests_cannot_use_the_profile(): void
    {
        $this->getJson('/api/profile')->assertUnauthorized();
        $this->postJson('/api/profile/cv')->assertUnauthorized();
    }

    public function test_profile_is_saved_and_the_national_number_is_encrypted_and_masked(): void
    {
        $user = $this->login();

        $this->putJson('/api/profile', [
            'phone' => '+20 100 123 4567',
            'headline' => 'Laravel developer',
            'skills' => ['PHP', 'php', ' Laravel '],
            'national_number' => '2950312 0101234',
        ])->assertOk()
            ->assertJsonPath('profile.birth_date', '1995-03-12') // derived from the number
            ->assertJsonPath('profile.skills', ['PHP', 'Laravel'])
            ->assertJsonPath('profile.national_number_masked', '••••••••••1234')
            ->assertJsonMissingPath('profile.national_number');

        $raw = \DB::table('users')->where('id', $user->id)->value('national_number');
        $this->assertStringNotContainsString('29503120101234', (string) $raw);

        $this->getJson('/api/profile/national-number')->assertOk()->assertJsonPath('national_number', '29503120101234');
        $this->getJson('/api/auth/me')->assertJsonMissingPath('user.national_number');
    }

    public function test_birth_date_must_match_the_national_number(): void
    {
        $this->login();

        $this->putJson('/api/profile', ['national_number' => '29503120101234', 'birth_date' => '1990-01-01'])
            ->assertStatus(422)->assertJsonValidationErrors('birth_date');
        $this->putJson('/api/profile', ['national_number' => '29513320101234'])
            ->assertStatus(422)->assertJsonValidationErrors('national_number');
    }

    public function test_photo_is_resized_stored_privately_and_served_only_to_its_owner(): void
    {
        $user = $this->login();

        $this->postJson('/api/profile/photo', ['photo' => UploadedFile::fake()->image('me.png', 900, 600)])
            ->assertOk()->assertJsonPath('profile.has_photo', true);

        $path = $user->fresh()->photo_path;
        Storage::disk('local')->assertExists($path);
        [$w, $h] = getimagesizefromstring(Storage::disk('local')->get($path));
        $this->assertSame([512, 512], [$w, $h]);

        $this->get('/api/profile/photo')->assertOk();
        $this->deleteJson('/api/profile/photo')->assertOk()->assertJsonPath('profile.has_photo', false);
        Storage::disk('local')->assertMissing($path);

        $this->postJson('/api/profile/photo', ['photo' => UploadedFile::fake()->create('x.exe', 10, 'application/octet-stream')])
            ->assertStatus(422);
    }

    public function test_cv_upload_returns_autofill_guesses_without_saving_them(): void
    {
        $user = $this->login();

        $cv = $this->docx("Sara Ali Hassan\nData Analyst\nPhone: 01012345678\nDate of Birth: 03/05/1996\nSKILLS\nSQL, Python");
        $res = $this->postJson('/api/profile/cv', ['cv' => $cv])->assertCreated()
            ->assertJsonPath('profile.has_cv', true)
            ->assertJsonPath('autofill.readable', true)
            ->assertJsonPath('autofill.fields.name', 'Sara Ali Hassan')
            ->assertJsonPath('autofill.fields.phone', '01012345678')
            ->assertJsonPath('autofill.fields.birth_date', '1996-05-03');
        $this->assertContains('Python', $res->json('autofill.fields.skills'));

        $this->assertNull($user->fresh()->phone); // guesses are only suggestions
        $this->postJson('/api/profile/cv/autofill')->assertOk()->assertJsonPath('autofill.fields.headline', 'Data Analyst');
        $this->get('/api/profile/cv')->assertOk()->assertDownload('My CV.docx');

        $this->deleteJson('/api/profile/cv')->assertOk()->assertJsonPath('profile.has_cv', false);
        $this->postJson('/api/profile/cv/autofill')->assertStatus(422);
    }

    public function test_cv_must_really_be_a_pdf_or_docx(): void
    {
        $this->login();

        $fake = UploadedFile::fake()->createWithContent('cv.pdf', '<?php echo 1;');
        $this->postJson('/api/profile/cv', ['cv' => $fake])->assertStatus(422)->assertJsonValidationErrors('cv');
        $this->postJson('/api/profile/cv', ['cv' => UploadedFile::fake()->create('cv.txt', 1)])->assertStatus(422);
    }
}
