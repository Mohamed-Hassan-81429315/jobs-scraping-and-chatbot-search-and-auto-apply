<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('users', function (Blueprint $table) {
            $table->string('phone', 32)->nullable();
            $table->string('headline', 120)->nullable();
            $table->string('location', 120)->nullable();
            $table->text('summary')->nullable();
            $table->json('skills')->nullable();
            $table->text('national_number')->nullable(); // encrypted by the model cast
            $table->date('birth_date')->nullable();
            $table->string('photo_path')->nullable();
            $table->string('cv_path')->nullable();
            $table->string('cv_name', 160)->nullable();
            $table->timestamp('cv_uploaded_at')->nullable();
        });
    }

    public function down(): void
    {
        Schema::table('users', function (Blueprint $table) {
            $table->dropColumn([
                'phone', 'headline', 'location', 'summary', 'skills', 'national_number',
                'birth_date', 'photo_path', 'cv_path', 'cv_name', 'cv_uploaded_at',
            ]);
        });
    }
};
