<?php

namespace App\Http\Controllers;

use App\Models\ChatConversation;
use Illuminate\Database\UniqueConstraintViolationException;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

class ChatController extends Controller
{
    private const DEFAULT_TITLE = 'New chat';

    public function index(Request $request): JsonResponse
    {
        $rows = ChatConversation::where('user_id', $request->user()->id)
            ->orderByDesc('updated_at')
            ->orderByDesc('id')
            ->limit(200)
            ->get(['id', 'title', 'updated_at']);

        return response()->json(['conversations' => $rows]);
    }

    /**
     * Create a conversation. Optionally with its messages (used when a guest chat
     * is imported right after login). client_uuid makes a retry return the same chat.
     */
    public function store(Request $request): JsonResponse
    {
        $data = $request->validate($this->rules(true));
        $user = $request->user();
        $uuid = $data['client_uuid'] ?? null;

        if ($uuid && ($existing = $this->findByClientUuid($user->id, $uuid))) {
            return $this->respond($existing);
        }

        try {
            $conversation = DB::transaction(function () use ($data, $user, $uuid) {
                $messages = $data['messages'] ?? [];

                $conversation = ChatConversation::create([
                    'user_id' => $user->id,
                    'client_uuid' => $uuid,
                    'title' => $data['title'] ?? $this->titleFrom($messages),
                ]);

                $this->appendMessages($conversation, $messages);

                return $conversation;
            });
        } catch (UniqueConstraintViolationException $e) {
            // Two requests with the same client_uuid raced: return the winner.
            if ($uuid && ($existing = $this->findByClientUuid($user->id, $uuid))) {
                return $this->respond($existing);
            }
            throw $e;
        }

        return $this->respond($conversation, 201);
    }

    public function show(Request $request, int $id): JsonResponse
    {
        return $this->respond($this->owned($request, $id));
    }

    public function append(Request $request, int $id): JsonResponse
    {
        $conversation = $this->owned($request, $id);
        $data = $request->validate($this->rules(false));

        DB::transaction(function () use ($conversation, $data) {
            $locked = ChatConversation::whereKey($conversation->id)->lockForUpdate()->first();
            $this->appendMessages($locked, $data['messages']);
        });

        return response()->json(['ok' => true]);
    }

    public function update(Request $request, int $id): JsonResponse
    {
        $conversation = $this->owned($request, $id);
        $data = $request->validate(['title' => ['required', 'string', 'min:1', 'max:120']]);

        $conversation->update(['title' => trim($data['title'])]);

        return response()->json(['ok' => true]);
    }

    public function destroy(Request $request, int $id): JsonResponse
    {
        $this->owned($request, $id)->delete(); // messages cascade

        return response()->json(['ok' => true]);
    }

    // ------------------------------------------------------------------

    /** A conversation that belongs to the current user, or 404. Never leaks other users' chats. */
    private function owned(Request $request, int $id): ChatConversation
    {
        return ChatConversation::where('user_id', $request->user()->id)
            ->whereKey($id)
            ->firstOrFail();
    }

    private function findByClientUuid(int $userId, string $uuid): ?ChatConversation
    {
        return ChatConversation::where('user_id', $userId)->where('client_uuid', $uuid)->first();
    }

    private function rules(bool $creating): array
    {
        $meta = [
            'nullable',
            'array',
            function ($attribute, $value, $fail) {
                if (strlen((string) json_encode($value)) > 50000) {
                    $fail('Message metadata is too large.');
                }
            },
        ];

        return [
            ...($creating
                ? ['client_uuid' => ['nullable', 'uuid'], 'title' => ['nullable', 'string', 'max:120']]
                : []),
            'messages' => $creating ? ['nullable', 'array', 'max:200'] : ['required', 'array', 'min:1', 'max:50'],
            'messages.*.role' => ['required', 'in:user,assistant'],
            'messages.*.content' => ['required', 'string', 'max:20000'],
            'messages.*.meta' => $meta,
        ];
    }

    /** Append in order: position continues from the last stored message. */
    private function appendMessages(ChatConversation $conversation, array $messages): void
    {
        if (!$messages) {
            return;
        }

        $position = (int) $conversation->messages()->max('position');

        foreach ($messages as $m) {
            $position++;
            $conversation->messages()->create([
                'position' => $position,
                'role' => $m['role'],
                'content' => $m['content'],
                'meta' => $m['meta'] ?? null,
            ]);
        }

        if ($conversation->title === self::DEFAULT_TITLE) {
            $conversation->title = $this->titleFrom($messages);
        }
        $conversation->updated_at = now();
        $conversation->save();
    }

    private function titleFrom(array $messages): string
    {
        foreach ($messages as $m) {
            if (($m['role'] ?? '') === 'user') {
                $title = Str::limit(trim((string) preg_replace('/\s+/u', ' ', $m['content'])), 60, '…');
                if ($title !== '') {
                    return $title;
                }
            }
        }

        return self::DEFAULT_TITLE;
    }

    private function respond(ChatConversation $conversation, int $status = 200): JsonResponse
    {
        $conversation->load(['messages' => fn ($q) => $q->orderBy('position')]);

        return response()->json([
            'conversation' => [
                'id' => $conversation->id,
                'title' => $conversation->title,
                'updated_at' => $conversation->updated_at?->toIso8601String(),
                'messages' => $conversation->messages->map(fn ($m) => [
                    'id' => $m->id,
                    'role' => $m->role,
                    'content' => $m->content,
                    'meta' => $m->meta,
                    'created_at' => $m->created_at?->toIso8601String(),
                ])->values(),
            ],
        ], $status);
    }
}
