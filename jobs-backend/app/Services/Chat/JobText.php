<?php

namespace App\Services\Chat;

use App\Models\Job;
use Illuminate\Support\Str;

/**
 * One text template for jobs AND for queries, so both sit in the same
 * "shape" in embedding space and cosine scores are meaningful.
 */
class JobText
{
    /** Bump when the Qdrant payload layout changes; jobs:embed then refreshes payloads without re-embedding. */
    public const VERSION = 2;

    private const LOCATION_STOP = [
        'remote', 'anywhere', 'worldwide', 'hybrid', 'onsite', 'site', 'and', 'the', 'area', 'region',
        'city', 'province', 'state', 'county', 'district', 'metropolitan', 'greater', 'office', 'home',
        'work', 'from', 'wfh', 'in', 'of', 'on', 'at', 'or', 'to', 'de', 'la', 'el',
    ];

    public static function remote(string $source, string $title, ?string $location, array $tags): bool
    {
        if (in_array($source, ['remoteok', 'remotive'], true)) {
            return true;
        }

        $haystack = mb_strtolower($title . ' ' . $location . ' ' . implode(' ', $tags));

        return (bool) preg_match('/\bremote\b|home\s?-?office|work from home|\bwfh\b/u', $haystack);
    }

    /** Lowercased ASCII words of a place name ("Zürich, Switzerland" => zurich, switzerland). */
    public static function locationTokens(?string $location): array
    {
        $ascii = mb_strtolower(Str::ascii((string) $location));
        $words = preg_split('/[^a-z0-9]+/', $ascii, -1, PREG_SPLIT_NO_EMPTY) ?: [];

        $tokens = [];
        foreach ($words as $word) {
            if (strlen($word) >= 2 && !in_array($word, self::LOCATION_STOP, true)) {
                $tokens[$word] = true;
            }
        }

        return array_slice(array_keys($tokens), 0, 12);
    }

    public static function hash(string $text): string
    {
        return md5($text);
    }

    /** Requires the company, source and tags relations to be loaded. */
    public static function forJob(Job $job): string
    {
        $tags  = $job->tags->pluck('name')->all();
        $plain = trim((string) preg_replace(
            '/\s+/u',
            ' ',
            strip_tags(html_entity_decode((string) $job->description))
        ));

        $lines = [
            'Title: ' . $job->title,
            'Company: ' . $job->company->name,
            'Location: ' . ($job->location ?: 'not specified'),
            'Remote: ' . (self::remote($job->source->name, $job->title, $job->location, $tags) ? 'yes' : 'no'),
        ];
        if ($tags) {
            $lines[] = 'Skills: ' . implode(', ', array_slice($tags, 0, 10));
        }
        if ($plain !== '') {
            $lines[] = 'Summary: ' . mb_substr($plain, 0, 700);
        }

        return implode("\n", $lines);
    }

    /** Turns the validated JSON search plan into the text that gets embedded. */
    public static function forQuery(array $s): string
    {
        $lines = [];

        if ($s['titles']) {
            $lines[] = 'Title: ' . implode(' / ', $s['titles']);
        }
        if ($s['seniority']) {
            $lines[] = 'Seniority: ' . $s['seniority'];
        }
        if ($s['employment_type']) {
            $lines[] = 'Employment type: ' . $s['employment_type'];
        }
        if ($s['location'] !== '') {
            $lines[] = 'Location: ' . $s['location'];
        }
        if ($s['remote'] === true) {
            $lines[] = 'Remote: yes';
        }
        if ($s['skills']) {
            $lines[] = 'Skills: ' . implode(', ', $s['skills']);
        }
        if ($s['semantic_query'] !== '') {
            $lines[] = 'Summary: ' . $s['semantic_query'];
        }

        return implode("\n", $lines);
    }

    public static function payload(Job $job, string $hash): array
    {
        $tags = $job->tags->pluck('name')->all();

        return [
            'job_id'          => $job->id,
            'source'          => $job->source->name,
            'remote'          => self::remote($job->source->name, $job->title, $job->location, $tags),
            'posted_ts'       => $job->posted_at?->timestamp,
            'location_tokens' => self::locationTokens($job->location),
            'hash'            => $hash,
            'pv'              => self::VERSION,
        ];
    }
}
