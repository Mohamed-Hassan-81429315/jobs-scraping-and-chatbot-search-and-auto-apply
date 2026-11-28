<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Foundation\Auth\User as Authenticatable;
use Illuminate\Notifications\Notifiable;
use Laravel\Sanctum\HasApiTokens;

class User extends Authenticatable
{
    use HasApiTokens, HasFactory, Notifiable;

    protected $fillable = ['name', 'email', 'password', 'phone', 'headline', 'location', 'summary', 'skills', 'national_number', 'birth_date', 'photo_path', 'cv_path', 'cv_name', 'cv_uploaded_at'];

    protected $hidden = ['password', 'remember_token', 'national_number', 'photo_path', 'cv_path'];

    protected function casts(): array
    {
        return [
            'national_number' => 'encrypted',
            'birth_date' => 'date:Y-m-d',
            'skills' => 'array',
            'cv_uploaded_at' => 'datetime',
            'email_verified_at' => 'datetime',
            'password'          => 'hashed',
        ];
    }
}
