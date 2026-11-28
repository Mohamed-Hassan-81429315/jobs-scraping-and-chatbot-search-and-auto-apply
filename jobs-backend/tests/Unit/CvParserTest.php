<?php

namespace Tests\Unit;

use App\Services\CvParser;
use PHPUnit\Framework\TestCase;

class CvParserTest extends TestCase
{
    public function test_it_reads_the_common_fields(): void
    {
        $r = (new CvParser())->parse("Mohamed Hassan\nSenior PHP Developer\nmo@example.com | +20 100 123 4567\nNational ID: 29503120101234\nAddress: Cairo, Egypt\nSKILLS\nPHP, Laravel, Docker\n");

        $this->assertSame('Mohamed Hassan', $r['name']);
        $this->assertSame('Senior PHP Developer', $r['headline']);
        $this->assertSame('mo@example.com', $r['email']);
        $this->assertSame('+20 100 123 4567', $r['phone']);
        $this->assertSame('29503120101234', $r['national_number']);
        $this->assertSame('1995-03-12', $r['birth_date']);
        $this->assertSame('Cairo, Egypt', $r['location']);
        $this->assertContains('Laravel', $r['skills']);
    }

    public function test_it_reads_arabic_digits_and_ignores_year_ranges(): void
    {
        $r = (new CvParser())->parse("أحمد علي محمود\nالرقم القومي: ٢٩٩٠١٠١٠١٢٣٤٥٦\nExperience 2019 - 2023\n");

        $this->assertSame('29901010123456', $r['national_number']);
        $this->assertNull($r['phone']);
    }

    public function test_it_never_invents_values(): void
    {
        $r = (new CvParser())->parse("just some words here\n");

        $this->assertNull($r['email']);
        $this->assertNull($r['national_number']);
        $this->assertNull($r['birth_date']);
        $this->assertSame([], $r['skills']);
    }

    public function test_birth_date_comes_only_from_a_valid_national_number(): void
    {
        $this->assertSame('2004-02-29', CvParser::birthFromNationalNumber('30402290100001'));
        $this->assertNull(CvParser::birthFromNationalNumber('29513320101234'));
        $this->assertNull(CvParser::birthFromNationalNumber('12345'));
    }
}
