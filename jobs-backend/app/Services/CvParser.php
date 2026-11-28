<?php

namespace App\Services;

use ZipArchive;

/**
 * Reads a CV (PDF or DOCX) and guesses profile fields from its text.
 * Heuristics only (no AI, no network): it never invents data, and every guess is shown to the
 * user to review before anything is saved.
 */
class CvParser
{
    private const MAX_CHARS = 60000;

    private const HEADINGS = '(?:summary|profile|about(?:\s+me)?|objective|career\s+objective|professional\s+summary|experience|work\s+experience|employment|education|skills|technical\s+skills|key\s+skills|core\s+skills|projects|certifications?|courses|languages|references|interests|contact|personal\s+(?:details|information|data)|نبذة|الملخص|الخبرات?|الخبرة|التعليم|المهارات|اللغات|المشاريع|الدورات)';

    private const SKILLS = [
        'PHP', 'Laravel', 'Symfony', 'WordPress', 'JavaScript', 'TypeScript', 'React', 'Next.js', 'Vue.js', 'Angular',
        'Node.js', 'Express', 'NestJS', 'Python', 'Django', 'Flask', 'FastAPI', 'Java', 'Spring Boot', 'Kotlin', 'Swift',
        'C#', '.NET', 'ASP.NET', 'C++', 'Go', 'Rust', 'Ruby', 'Rails', 'SQL', 'MySQL', 'PostgreSQL', 'MongoDB', 'Redis',
        'Elasticsearch', 'Qdrant', 'GraphQL', 'REST API', 'HTML', 'CSS', 'Sass', 'Tailwind CSS', 'Bootstrap', 'jQuery',
        'Docker', 'Kubernetes', 'AWS', 'Azure', 'Google Cloud', 'Linux', 'Git', 'GitHub', 'GitLab', 'CI/CD', 'Jenkins',
        'Terraform', 'Ansible', 'Nginx', 'Apache', 'Firebase', 'Flutter', 'React Native', 'Android', 'iOS', 'Figma',
        'Photoshop', 'Illustrator', 'UI/UX', 'Machine Learning', 'Deep Learning', 'Data Analysis', 'Pandas', 'NumPy',
        'TensorFlow', 'PyTorch', 'OpenAI', 'Power BI', 'Tableau', 'Excel', 'Selenium', 'Jest', 'PHPUnit', 'Cypress',
        'Agile', 'Scrum', 'Jira', 'Microservices', 'OOP', 'Design Patterns', 'SEO', 'Digital Marketing', 'Accounting',
        'Project Management', 'Customer Service', 'Communication', 'Leadership', 'Teamwork', 'Problem Solving',
    ];

    private const TITLE_WORDS = '(?:engineer|developer|programmer|designer|analyst|manager|architect|consultant|specialist|administrator|officer|accountant|scientist|technician|lead|director|intern|coordinator|marketer|executive|مهندس|مطور|مبرمج|محلل|مصمم|محاسب|مدير|مسؤول|أخصائي)';

    /** Text of the file, or '' if it cannot be read (the caller then says so). */
    public function extractText(string $path, string $extension): string
    {
        $extension = strtolower($extension);

        return $this->limit(match ($extension) {
            'pdf' => $this->pdfText($path),
            'docx' => $this->docxText($path),
            default => '',
        });
    }

    private function pdfText(string $path): string
    {
        if (class_exists(\Smalot\PdfParser\Parser::class)) {
            try {
                return (string) (new \Smalot\PdfParser\Parser())->parseFile($path)->getText();
            } catch (\Throwable) {
                // fall through to pdftotext
            }
        }

        if (function_exists('proc_open') && is_executable('/usr/bin/pdftotext')) {
            try {
                $proc = new \Symfony\Component\Process\Process(['/usr/bin/pdftotext', '-layout', '-enc', 'UTF-8', $path, '-']);
                $proc->setTimeout(15)->run();

                return $proc->isSuccessful() ? $proc->getOutput() : '';
            } catch (\Throwable) {
                return '';
            }
        }

        return '';
    }

    private function docxText(string $path): string
    {
        if (!class_exists(ZipArchive::class)) {
            return '';
        }
        $zip = new ZipArchive();
        if ($zip->open($path) !== true) {
            return '';
        }
        try {
            $stat = $zip->statName('word/document.xml');
            if (!$stat || $stat['size'] > 8 * 1024 * 1024) { // refuse zip bombs
                return '';
            }
            $xml = (string) $zip->getFromName('word/document.xml');
        } finally {
            $zip->close();
        }
        $xml = preg_replace('~</w:p>|<w:br\s*/?>~', "\n", $xml);
        $xml = preg_replace('~<w:tab\s*/?>~', ' ', $xml);

        return html_entity_decode(strip_tags($xml), ENT_QUOTES | ENT_XML1, 'UTF-8');
    }

    /** @return array{name:?string,email:?string,phone:?string,headline:?string,location:?string,summary:?string,skills:array,birth_date:?string,national_number:?string} */
    public function parse(string $text): array
    {
        $text = $this->limit($this->normalize($text));
        $lines = array_values(array_filter(array_map('trim', explode("\n", $text)), fn ($l) => $l !== ''));

        $national = $this->nationalNumber($text);
        $name = $this->name($lines);

        return [
            'name' => $name,
            'email' => $this->email($text),
            'phone' => $this->phone($text, $national),
            'headline' => $this->headline($lines, $name),
            'location' => $this->location($text),
            'summary' => $this->summary($text),
            'skills' => $this->skills($text),
            'birth_date' => $this->birthDate($text) ?? ($national ? self::birthFromNationalNumber($national) : null),
            'national_number' => $national,
        ];
    }

    /** Egyptian 14-digit number: C YYMMDD GG SSSS D, C = 2 (1900s) or 3 (2000s). Returns Y-m-d or null. */
    public static function birthFromNationalNumber(string $number): ?string
    {
        if (!preg_match('/^([23])(\d{2})(\d{2})(\d{2})\d{7}$/', $number, $m)) {
            return null;
        }
        $year = ($m[1] === '2' ? 1900 : 2000) + (int) $m[2];
        if (!checkdate((int) $m[3], (int) $m[4], $year) || $year > (int) date('Y')) {
            return null;
        }

        return sprintf('%04d-%02d-%02d', $year, $m[3], $m[4]);
    }

    private function normalize(string $text): string
    {
        $text = strtr($text, ['٠' => '0', '١' => '1', '٢' => '2', '٣' => '3', '٤' => '4', '٥' => '5', '٦' => '6', '٧' => '7', '٨' => '8', '٩' => '9']);
        $text = str_replace(["\r\n", "\r", "\u{00A0}", "\t"], ["\n", "\n", ' ', ' '], $text);
        $text = preg_replace('/[^\P{C}\n]+/u', '', $text) ?? $text; // drop control characters

        return $text;
    }

    private function limit(string $text): string
    {
        return mb_substr($text, 0, self::MAX_CHARS);
    }

    private function email(string $text): ?string
    {
        return preg_match('/[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}/i', $text, $m) ? strtolower($m[0]) : null;
    }

    private function nationalNumber(string $text): ?string
    {
        $label = '(?:national\s*(?:id|number|no\.?)|id\s*(?:number|no\.?)|الرقم\s*القومي|رقم\s*قومي)';
        if (preg_match('/' . $label . '\s*[:\-#]?\s*((?:\d[\s\-]?){14})/iu', $text, $m)) {
            $digits = preg_replace('/\D/', '', $m[1]);
            if (self::birthFromNationalNumber($digits)) {
                return $digits;
            }
        }
        if (preg_match_all('/(?<!\d)[23]\d{13}(?!\d)/', $text, $all)) {
            foreach ($all[0] as $candidate) {
                if (self::birthFromNationalNumber($candidate)) {
                    return $candidate;
                }
            }
        }

        return null;
    }

    private function phone(string $text, ?string $national): ?string
    {
        $labelled = '/(?:phone|mobile|tel|cell|whatsapp|contact|call|هاتف|موبايل|محمول|جوال)\s*(?:no\.?|number)?\s*[:\-]?\s*(\+?\d[\d\s().\-]{7,20}\d)/iu';
        $any = '/(?<![\d])(\+?\d[\d\s().\-]{7,20}\d)(?![\d])/';

        foreach ([$labelled, $any] as $pattern) {
            if (preg_match_all($pattern, $text, $all)) {
                foreach ($all[1] as $candidate) {
                    $digits = preg_replace('/\D/', '', $candidate);
                    if (strlen($digits) < 9 || strlen($digits) > 15 || $digits === $national) {
                        continue;
                    }
                    if (preg_match('/^(19|20)\d{2}\D+(19|20)\d{2}/', trim($candidate))) {
                        continue; // a year range such as 2019 - 2023
                    }

                    return preg_replace('/\s+/', ' ', trim($candidate));
                }
            }
        }

        return null;
    }

    private function birthDate(string $text): ?string
    {
        $label = '(?:date\s*of\s*birth|birth\s*date|birthday|d\.?o\.?b\.?|born(?:\s*on)?|تاريخ\s*الميلاد|مواليد)';
        if (!preg_match('/' . $label . '\s*[:\-]?\s*([^\n]{6,30})/iu', $text, $m)) {
            return null;
        }
        $raw = trim($m[1]);

        if (preg_match('/(\d{4})[\/\-.](\d{1,2})[\/\-.](\d{1,2})/', $raw, $d)) {
            return $this->ymd((int) $d[1], (int) $d[2], (int) $d[3]);
        }
        if (preg_match('/(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{4})/', $raw, $d)) {
            return $this->ymd((int) $d[3], (int) $d[2], (int) $d[1]); // day first (Egypt/Europe)
        }
        $months = ['jan' => 1, 'feb' => 2, 'mar' => 3, 'apr' => 4, 'may' => 5, 'jun' => 6, 'jul' => 7, 'aug' => 8, 'sep' => 9, 'oct' => 10, 'nov' => 11, 'dec' => 12];
        if (preg_match('/(\d{1,2})(?:st|nd|rd|th)?\s+([a-z]{3})[a-z]*\.?,?\s+(\d{4})/i', $raw, $d) && isset($months[strtolower($d[2])])) {
            return $this->ymd((int) $d[3], $months[strtolower($d[2])], (int) $d[1]);
        }
        if (preg_match('/([a-z]{3})[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})/i', $raw, $d) && isset($months[strtolower($d[1])])) {
            return $this->ymd((int) $d[3], $months[strtolower($d[1])], (int) $d[2]);
        }

        return null;
    }

    private function ymd(int $y, int $m, int $d): ?string
    {
        return checkdate($m, $d, $y) && $y >= 1900 && $y <= (int) date('Y') ? sprintf('%04d-%02d-%02d', $y, $m, $d) : null;
    }

    private function name(array $lines): ?string
    {
        foreach (array_slice($lines, 0, 8) as $line) {
            $clean = trim(preg_replace('/\s+/', ' ', $line));
            if (preg_match('/curriculum|resume|\bcv\b|سيرة/iu', $clean) || preg_match('/[\d@:\/]/', $clean)) {
                continue;
            }
            $words = explode(' ', $clean);
            if (count($words) >= 2 && count($words) <= 5 && mb_strlen($clean) <= 60
                && preg_match('/^[\p{L}\'.\-\s]+$/u', $clean)
                && !preg_match('/' . self::TITLE_WORDS . '/iu', $clean)
                && !preg_match('/^' . self::HEADINGS . '$/iu', $clean)) {
                return $clean;
            }
        }

        return null;
    }

    private function headline(array $lines, ?string $name): ?string
    {
        foreach (array_slice($lines, 0, 12) as $line) {
            $clean = trim(preg_replace('/\s+/', ' ', $line));
            if ($clean === $name || mb_strlen($clean) > 80 || preg_match('/[@\d]{3,}/', $clean)) {
                continue;
            }
            if (preg_match('/' . self::TITLE_WORDS . '/iu', $clean)) {
                return $clean;
            }
        }

        return null;
    }

    private function location(string $text): ?string
    {
        if (preg_match('/(?:address|location|city|based\s+in|العنوان|المدينة)\s*[:\-]\s*([^\n]{3,80})/iu', $text, $m)) {
            return trim(preg_replace('/\s+/', ' ', $m[1]), " \t,.;");
        }

        return null;
    }

    private function section(string $text, string $headingPattern): ?string
    {
        $re = '/^\s*' . $headingPattern . '\s*:?\s*$/imu';
        if (!preg_match($re, $text, $m, PREG_OFFSET_CAPTURE)) {
            return null;
        }
        $rest = substr($text, $m[0][1] + strlen($m[0][0]));
        $parts = preg_split('/^\s*' . self::HEADINGS . '\s*:?\s*$/imu', $rest, 2);

        return trim($parts[0]) !== '' ? trim($parts[0]) : null;
    }

    private function summary(string $text): ?string
    {
        $body = $this->section($text, '(?:summary|profile|about(?:\s+me)?|objective|career\s+objective|professional\s+summary|نبذة|الملخص)');
        if (!$body) {
            return null;
        }
        $body = trim(preg_replace('/\s+/', ' ', $body));

        return mb_strlen($body) > 600 ? rtrim(mb_substr($body, 0, 597)) . '...' : $body;
    }

    /** @return string[] */
    private function skills(string $text): array
    {
        $found = [];
        foreach (self::SKILLS as $skill) {
            $quoted = preg_quote($skill, '/');
            if (preg_match('/(?<![\p{L}\d+#])' . $quoted . '(?![\p{L}\d+#])/iu', $text)) {
                $found[strtolower($skill)] = $skill;
            }
        }

        $body = $this->section($text, '(?:(?:technical|key|core)\s+)?skills|المهارات');
        if ($body) {
            foreach (preg_split('/[,;،|•·●▪\n]+/u', $body) as $item) {
                $item = trim($item, " \t-–—*:.");
                if ($item !== '' && mb_strlen($item) <= 30 && !preg_match('/[@\/]{2}|^\d+$/', $item)) {
                    $found[mb_strtolower($item)] ??= $item;
                }
            }
        }

        return array_slice(array_values($found), 0, 30);
    }
}
