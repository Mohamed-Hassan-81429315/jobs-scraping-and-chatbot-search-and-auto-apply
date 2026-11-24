<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('chat_conversations', function (Blueprint $table) {
            $table->id();
            $table->foreignId('user_id')->constrained()->cascadeOnDelete();
            // Generated in the browser. Makes "import my guest chat" idempotent.
            $table->uuid('client_uuid')->nullable();
            $table->string('title', 120)->default('New chat');
            $table->timestamps();

            $table->index(['user_id', 'updated_at']);
            $table->unique(['user_id', 'client_uuid']);
        });

        Schema::create('chat_messages', function (Blueprint $table) {
            $table->id();
            $table->foreignId('conversation_id')->constrained('chat_conversations')->cascadeOnDelete();
            // 1, 2, 3 ... the order the messages were sent. Never sort by timestamp.
            $table->unsignedInteger('position');
            $table->string('role', 16); // user | assistant
            $table->longText('content');
            $table->json('meta')->nullable(); // e.g. job cards the bot returned
            $table->timestamps();

            $table->unique(['conversation_id', 'position']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('chat_messages');
        Schema::dropIfExists('chat_conversations');
    }
};
