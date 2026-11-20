<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('sources', function (Blueprint $t) {
            $t->id();
            $t->string('name', 100)->unique();
            $t->timestamps();
        });

        Schema::create('companies', function (Blueprint $t) {
            $t->id();
            $t->string('name')->unique();
            $t->timestamps();
        });

        Schema::create('jobs', function (Blueprint $t) {
            $t->id();
            $t->char('external_id', 32)->unique();   // md5 id from the scraper
            $t->foreignId('source_id')->constrained()->cascadeOnDelete();
            $t->foreignId('company_id')->constrained()->cascadeOnDelete();
            $t->string('title', 500);
            $t->string('location', 500)->nullable();
            $t->text('url');
            $t->timestamp('posted_at')->nullable()->index();
            $t->longText('description')->nullable();
            $t->timestamps();
            $t->index('title');
        });

        Schema::create('tags', function (Blueprint $t) {
            $t->id();
            $t->string('name', 190)->unique();
        });

        Schema::create('job_tag', function (Blueprint $t) {
            $t->foreignId('job_id')->constrained()->cascadeOnDelete();
            $t->foreignId('tag_id')->constrained()->cascadeOnDelete();
            $t->primary(['job_id', 'tag_id']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('job_tag');
        Schema::dropIfExists('tags');
        Schema::dropIfExists('jobs');
        Schema::dropIfExists('companies');
        Schema::dropIfExists('sources');
    }
};