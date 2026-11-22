<?php

namespace App\Services\Chat;

/**
 * Place names. The planner prompt returns the location exactly as the user wrote it (it can be Arabic) and
 * gives no aliases, so this class turns Arabic names into English ones and adds the country of a city
 * (or the main cities of a country), which is what the location filter matches against.
 */
class Places
{
    /** Arabic place names => English name (spelling variants are folded by norm()). */
    private const AR = [
        // Egypt
        'القاهرة' => 'Cairo', 'الجيزة' => 'Giza', 'الإسكندرية' => 'Alexandria', 'مصر' => 'Egypt',
        'التجمع الخامس' => 'New Cairo', 'القاهرة الجديدة' => 'New Cairo', 'مدينة نصر' => 'Nasr City',
        'السادس من أكتوبر' => '6th of October', 'العاصمة الإدارية' => 'New Administrative Capital',
        'المنصورة' => 'Mansoura', 'طنطا' => 'Tanta', 'أسيوط' => 'Assiut', 'الغردقة' => 'Hurghada',
        'شرم الشيخ' => 'Sharm El Sheikh', 'بورسعيد' => 'Port Said', 'السويس' => 'Suez',
        // Gulf
        'الرياض' => 'Riyadh', 'جدة' => 'Jeddah', 'الدمام' => 'Dammam', 'الخبر' => 'Khobar', 'مكة' => 'Mecca',
        'المدينة المنورة' => 'Medina', 'السعودية' => 'Saudi Arabia', 'المملكة العربية السعودية' => 'Saudi Arabia',
        'دبي' => 'Dubai', 'أبوظبي' => 'Abu Dhabi', 'الشارقة' => 'Sharjah', 'الإمارات' => 'United Arab Emirates',
        'الكويت' => 'Kuwait', 'قطر' => 'Qatar', 'الدوحة' => 'Doha', 'البحرين' => 'Bahrain', 'المنامة' => 'Manama',
        'سلطنة عمان' => 'Oman', 'مسقط' => 'Muscat',
        // Levant, Iraq, Maghreb, others
        'عمان' => 'Amman', 'الأردن' => 'Jordan', 'لبنان' => 'Lebanon', 'بيروت' => 'Beirut', 'العراق' => 'Iraq',
        'بغداد' => 'Baghdad', 'سوريا' => 'Syria', 'دمشق' => 'Damascus', 'فلسطين' => 'Palestine', 'رام الله' => 'Ramallah',
        'المغرب' => 'Morocco', 'الدار البيضاء' => 'Casablanca', 'الرباط' => 'Rabat', 'تونس' => 'Tunisia',
        'الجزائر' => 'Algeria', 'ليبيا' => 'Libya', 'طرابلس' => 'Tripoli', 'السودان' => 'Sudan', 'الخرطوم' => 'Khartoum',
        'اليمن' => 'Yemen',
        // Europe, Americas, Turkey
        'ألمانيا' => 'Germany', 'برلين' => 'Berlin', 'ميونخ' => 'Munich', 'هامبورغ' => 'Hamburg', 'فرانكفورت' => 'Frankfurt',
        'لندن' => 'London', 'بريطانيا' => 'United Kingdom', 'المملكة المتحدة' => 'United Kingdom', 'باريس' => 'Paris',
        'فرنسا' => 'France', 'هولندا' => 'Netherlands', 'أمستردام' => 'Amsterdam', 'إسبانيا' => 'Spain', 'مدريد' => 'Madrid',
        'إيطاليا' => 'Italy', 'تركيا' => 'Turkey', 'إسطنبول' => 'Istanbul', 'أيرلندا' => 'Ireland', 'دبلن' => 'Dublin',
        'كندا' => 'Canada', 'أمريكا' => 'United States', 'الولايات المتحدة' => 'United States', 'نيويورك' => 'New York',
    ];

    /** English city (lowercase) => its country. */
    private const CITY_COUNTRY = [
        'cairo' => 'Egypt', 'giza' => 'Egypt', 'alexandria' => 'Egypt', 'new cairo' => 'Egypt', 'nasr city' => 'Egypt',
        '6th of october' => 'Egypt', 'new administrative capital' => 'Egypt', 'mansoura' => 'Egypt', 'tanta' => 'Egypt',
        'assiut' => 'Egypt', 'hurghada' => 'Egypt', 'sharm el sheikh' => 'Egypt', 'port said' => 'Egypt', 'suez' => 'Egypt',
        'riyadh' => 'Saudi Arabia', 'jeddah' => 'Saudi Arabia', 'dammam' => 'Saudi Arabia', 'khobar' => 'Saudi Arabia',
        'mecca' => 'Saudi Arabia', 'medina' => 'Saudi Arabia',
        'dubai' => 'United Arab Emirates', 'abu dhabi' => 'United Arab Emirates', 'sharjah' => 'United Arab Emirates',
        'doha' => 'Qatar', 'manama' => 'Bahrain', 'muscat' => 'Oman', 'kuwait city' => 'Kuwait',
        'amman' => 'Jordan', 'beirut' => 'Lebanon', 'baghdad' => 'Iraq', 'damascus' => 'Syria', 'ramallah' => 'Palestine',
        'casablanca' => 'Morocco', 'rabat' => 'Morocco', 'tunis' => 'Tunisia', 'tripoli' => 'Libya', 'khartoum' => 'Sudan',
        'berlin' => 'Germany', 'munich' => 'Germany', 'hamburg' => 'Germany', 'frankfurt' => 'Germany',
        'london' => 'United Kingdom', 'manchester' => 'United Kingdom', 'paris' => 'France', 'amsterdam' => 'Netherlands',
        'madrid' => 'Spain', 'barcelona' => 'Spain', 'milan' => 'Italy', 'rome' => 'Italy', 'istanbul' => 'Turkey',
        'ankara' => 'Turkey', 'dublin' => 'Ireland', 'toronto' => 'Canada', 'vancouver' => 'Canada',
        'new york' => 'United States', 'san francisco' => 'United States', 'austin' => 'United States',
    ];

    /** English country (lowercase) => its main cities. */
    private const COUNTRY_CITIES = [
        'egypt' => ['Cairo', 'Giza', 'Alexandria'],
        'saudi arabia' => ['Riyadh', 'Jeddah', 'Dammam'],
        'united arab emirates' => ['Dubai', 'Abu Dhabi', 'Sharjah'],
        'qatar' => ['Doha'], 'bahrain' => ['Manama'], 'oman' => ['Muscat'], 'kuwait' => ['Kuwait City'],
        'jordan' => ['Amman'], 'lebanon' => ['Beirut'], 'iraq' => ['Baghdad'], 'morocco' => ['Casablanca', 'Rabat'],
        'tunisia' => ['Tunis'], 'germany' => ['Berlin', 'Munich', 'Hamburg', 'Frankfurt'],
        'united kingdom' => ['London', 'Manchester'], 'france' => ['Paris'], 'netherlands' => ['Amsterdam'],
        'spain' => ['Madrid', 'Barcelona'], 'italy' => ['Milan', 'Rome'], 'turkey' => ['Istanbul', 'Ankara'],
        'ireland' => ['Dublin'], 'canada' => ['Toronto', 'Vancouver'],
        'united states' => ['New York', 'San Francisco', 'Austin'],
    ];

    private const ABBREVIATIONS = [
        'uk' => 'United Kingdom', 'u.k.' => 'United Kingdom', 'uae' => 'United Arab Emirates', 'ksa' => 'Saudi Arabia',
        'usa' => 'United States', 'us' => 'United States', 'u.s.' => 'United States', 'america' => 'United States',
    ];

    /** @var array<string,string>|null normalized Arabic name => English */
    private static ?array $map = null;

    /** Removes diacritics and tatweel and folds the common Arabic letter variants, so spellings compare equal. */
    public static function norm(string $text): string
    {
        $text = (string) preg_replace('/[\x{064B}-\x{065F}\x{0670}\x{0640}]/u', '', $text);

        return strtr($text, ['أ' => 'ا', 'إ' => 'ا', 'آ' => 'ا', 'ى' => 'ي', 'ة' => 'ه']);
    }

    private static function map(): array
    {
        if (self::$map === null) {
            self::$map = [];
            foreach (self::AR as $ar => $en) {
                self::$map[self::norm($ar)] = $en;
            }
            // Longest names first, so "القاهرة الجديدة" wins over "القاهرة".
            uksort(self::$map, fn ($a, $b) => mb_strlen($b) <=> mb_strlen($a));
        }

        return self::$map;
    }

    private static function hasArabic(string $text): bool
    {
        return (bool) preg_match('/\p{Arabic}/u', $text);
    }

    /** English name of an Arabic place ("بالقاهرة" => Cairo). Text without Arabic letters is returned unchanged. */
    public static function toEnglish(string $location): string
    {
        $location = trim($location);
        if ($location === '' || !self::hasArabic($location)) {
            return $location;
        }

        $n = trim((string) preg_replace('/^(?:في|ب)(?=\s|ال)/u', '', self::norm($location)));
        $n = trim(preg_replace('/^بال/u', 'ال', $n) ?? $n);
        $map = self::map();

        foreach ([$n, preg_replace('/^ال/u', '', $n)] as $candidate) {
            if ($candidate !== '' && isset($map[$candidate])) {
                return $map[$candidate];
            }
            if ($candidate !== '' && isset($map['ال' . $candidate])) {
                return $map['ال' . $candidate];
            }
        }

        foreach ($map as $ar => $en) {
            if (mb_strpos($n, $ar) !== false) {
                return $en;
            }
        }

        return $location;
    }

    /** English names of every known Arabic place that appears inside $text (used for job locations). */
    public static function arabicToEnglish(string $text): string
    {
        if (!self::hasArabic($text)) {
            return '';
        }

        $n     = self::norm($text);
        $found = [];
        foreach (self::map() as $ar => $en) {
            if (mb_strpos($n, $ar) !== false) {
                $found[$en] = true;
                $n = str_replace($ar, ' ', $n); // do not also match the shorter name inside a longer one
            }
        }

        return implode(' ', array_keys($found));
    }

    /**
     * @return array{0:string,1:array<int,string>} English location name and up to 5 aliases
     *         (the country of a city, or the main cities of a country)
     */
    public static function resolve(string $location): array
    {
        $name = self::toEnglish($location);
        if ($name === '') {
            return ['', []];
        }

        $key = mb_strtolower($name);
        if (isset(self::ABBREVIATIONS[$key])) {
            $name = self::ABBREVIATIONS[$key];
            $key  = mb_strtolower($name);
        }

        $aliases = [];
        if (isset(self::CITY_COUNTRY[$key])) {
            $aliases[] = self::CITY_COUNTRY[$key];
        }
        foreach (self::COUNTRY_CITIES[$key] ?? [] as $city) {
            $aliases[] = $city;
        }

        return [$name, array_slice(array_values(array_unique($aliases)), 0, 5)];
    }
}
