<?php

namespace App\Http\Controllers;

use App\Services\JobSearch;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Str;

class ChatController extends Controller
{
    private const PLATFORMS = [
        'linkedin'        => 'LinkedIn',
        'indeed'          => 'Indeed',
        'glassdoor'       => 'Glassdoor',
        'odoo'            => 'Odoo',
        'smartrecruiters' => 'SmartRecruiters',
        'epam'            => 'EPAM',
        'remoteok'        => 'RemoteOK',
        'remotive'        => 'Remotive',
        'arbeitnow'       => 'Arbeitnow',
    ];

    private const STOPWORDS = [
        'a', 'an', 'the', 'i', 'me', 'my', 'we', 'you', 'is', 'are', 'am', 'can', 'could', 'would', 'please',
        'find', 'show', 'search', 'get', 'give', 'list', 'look', 'looking', 'want', 'need', 'any', 'some',
        'job', 'jobs', 'position', 'positions', 'role', 'roles', 'opening', 'openings', 'vacancy', 'vacancies',
        'work', 'for', 'in', 'at', 'near', 'around', 'on', 'of', 'to', 'with', 'from', 'and', 'available',
        'latest', 'newest', 'recent', 'new', 'there', 'do', 'have', 'has', 'about', 'related', 'that',
    ];

    public function message(Request $request, JobSearch $search): JsonResponse
    {
        $data  = $request->validate(['message' => ['required', 'string', 'max:300']]);
        $text  = trim((string) preg_replace('/\s+/u', ' ', $data['message']));
        $lower = Str::lower($text);

        if (preg_match('/^(hi|hello|hey|hola|salam|help|start|menu)\b/u', $lower)
            || str_contains($lower, 'what can you do')) {
            return $this->reply(
                "Hi! I can search every job in our database for you. Tell me a job title, skill, company or city, "
                . "and optionally a platform, \"remote\", or how recent the job should be.\n\n"
                . 'Try: remote Python jobs this week, Odoo developer, or data analyst in Berlin.'
            );
        }

        if (preg_match('/\b(thanks|thank you|thx)\b/u', $lower)) {
            return $this->reply('You are welcome! Ask me for another search any time.');
        }

        [$q, $source, $posted, $remote, $notes] = $this->parse($lower);

        if ($q === '' && $source === '' && $posted === '' && !$remote) {
            return $this->reply('What should I look for? Give me a job title, skill, company or city, for example "React developer in Cairo".');
        }

        try {
            $result = $search->search([
                'q'      => $q,
                'source' => $source,
                'posted' => $posted,
                'remote' => $remote ? '1' : '',
                'sort'   => $q === '' ? 'newest' : '',
                'page'   => 1,
            ]);
        } catch (\Throwable $e) {
            report($e);

            return $this->reply('The job search is temporarily unavailable. Please try again in a moment.');
        }

        $total = (int) ($result['total'] ?? 0);
        $what  = $q !== '' ? "“{$q}”" : 'that';
        $extra = $notes ? ' (' . implode(', ', $notes) . ')' : '';

        if ($total === 0) {
            return $this->reply(
                "I could not find jobs for {$what}{$extra}. Try fewer words or a related title, "
                . 'for example "developer" instead of "senior full-stack developer".'
            );
        }

        $top = array_map(fn ($j) => [
            'id'           => $j['id'],
            'title'        => $j['title'],
            'company'      => $j['company'],
            'location'     => $j['location'],
            'url'          => $j['url'],
            'source'       => $j['source'],
            'source_label' => self::PLATFORMS[$j['source']] ?? $j['source'],
            'posted_at'    => $j['posted_at'],
        ], array_slice($result['data'] ?? [], 0, 5));

        $query = array_filter([
            'q'      => $q,
            'source' => $source,
            'posted' => $posted,
            'remote' => $remote ? '1' : '',
        ], fn ($v) => $v !== '');

        $count = number_format($total);
        $word  = $total === 1 ? 'job' : 'jobs';
        $shown = count($top);

        return response()->json([
            'reply'      => "I found {$count} {$word} for {$what}{$extra}. Here " . ($shown === 1 ? 'is the top match:' : "are the top {$shown}:"),
            'jobs'       => $top,
            'total'      => $total,
            'search_url' => $query ? '/?' . http_build_query($query) : '/',
        ]);
    }

    /** @return array{0:string,1:string,2:string,3:bool,4:array<int,string>} */
    private function parse(string $lower): array
    {
        $rest   = ' ' . $lower . ' ';
        $source = '';
        $posted = '';
        $remote = false;
        $notes  = [];

        foreach (self::PLATFORMS as $key => $label) {
            $pattern = '/\b' . preg_quote($key, '/') . '\b/u';
            if (preg_match($pattern, $rest)) {
                $source  = $key;
                $notes[] = 'on ' . $label;
                $rest    = (string) preg_replace($pattern, ' ', $rest);
                break;
            }
        }

        $remotePattern = '/\b(remote|remotely|work from home|wfh|home ?office)\b/u';
        if (preg_match($remotePattern, $rest)) {
            $remote  = true;
            $notes[] = 'remote';
            $rest    = (string) preg_replace($remotePattern, ' ', $rest);
        }

        $windows = [
            '24h' => ['/\b(today|last 24 hours|past 24 hours|24 hours|24h|last day|past day)\b/u', 'posted in the last 24 hours'],
            '7d'  => ['/\b(this week|past week|last week|last 7 days|past 7 days|7 days)\b/u', 'posted in the last 7 days'],
            '30d' => ['/\b(this month|past month|last month|last 30 days|past 30 days|30 days)\b/u', 'posted in the last 30 days'],
        ];
        foreach ($windows as $key => [$pattern, $note]) {
            if (preg_match($pattern, $rest)) {
                $posted  = $key;
                $notes[] = $note;
                $rest    = (string) preg_replace($pattern, ' ', $rest);
                break;
            }
        }

        $words = [];
        $parts = preg_split('/\s+/u', trim($rest), -1, PREG_SPLIT_NO_EMPTY);
        foreach ($parts ?: [] as $word) {
            $word = trim($word, ',;:!?"()[]');
            if ($word === '' || in_array($word, self::STOPWORDS, true)) {
                continue;
            }
            $words[] = $word;
        }

        return [implode(' ', array_slice($words, 0, 8)), $source, $posted, $remote, $notes];
    }

    private function reply(string $text): JsonResponse
    {
        return response()->json([
            'reply'      => $text,
            'jobs'       => [],
            'total'      => 0,
            'search_url' => null,
        ]);
    }
}
