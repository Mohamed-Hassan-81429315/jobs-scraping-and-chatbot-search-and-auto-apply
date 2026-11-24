#!/usr/bin/env python3
"""
Hirelume: language toggle (English / Arabic, RTL) + light/dark theme toggle.

Run from the project root (the folder containing jobs-backend and jobs-frontend):

    python3 install_i18n_theme.py

FRONTEND
  * cookie-based language (hirelume_lang) with a header toggle; <html lang dir>
  * every user-facing string moved into lib/i18n/dictionaries/{en,ar}.js
  * RTL layout for Arabic (logical CSS properties, Arabic font)
  * light/dark theme (hirelume_theme cookie, follows the system until chosen),
    sun/moon toggle, one consolidated globals.css

BACKEND
  * validation messages, auth errors and chat replies follow the site language
    (X-Locale header, lang/ar.json, lang/ar/validation.php)
  * the chatbot ANSWERS in the website language, whatever language the user types in

Replaced files are backed up as <name>.prepatch (only the first time).
"""
import pathlib
import shutil
import sys

ROOT = pathlib.Path(".")
BACK = ROOT / "jobs-backend"
FRONT = ROOT / "jobs-frontend"

if not (BACK / "artisan").exists() or not (FRONT / "app" / "layout.js").exists():
    sys.exit("Run this from the project root (the folder that contains jobs-backend and jobs-frontend).")

if not (BACK / "app/Services/Chat/JobAssistant.php").exists():
    sys.exit("Run install_chatbot_openai.py first (JobAssistant.php is missing).")

FILES = {}

# =====================================================================
# FRONTEND: i18n core
# =====================================================================

FILES[FRONT / "lib/i18n/config.js"] = r'''export const LOCALES = ['en', 'ar'];
export const DEFAULT_LOCALE = 'en';
export const LOCALE_COOKIE = 'hirelume_lang';
export const THEME_COOKIE = 'hirelume_theme';
export const DIRECTION = { en: 'ltr', ar: 'rtl' };

// Arabic uses Latin digits so numbers match the job data.
export const INTL = { en: 'en-US', ar: 'ar-u-nu-latn' };

export const isLocale = (value) => LOCALES.includes(value);
'''

FILES[FRONT / "lib/i18n/translate.js"] = r'''import { INTL, DEFAULT_LOCALE } from './config';

/**
 * Builds a t(key, vars) function.
 *  - {name} placeholders are replaced; numbers are formatted for the locale.
 *  - When vars.count is a number, key.zero/one/two/few/many/other is chosen with Intl.PluralRules.
 */
export function createT(locale, messages) {
  const intl = INTL[locale] || INTL[DEFAULT_LOCALE];
  const numbers = new Intl.NumberFormat(intl);
  const plurals = new Intl.PluralRules(intl);

  function pick(key, vars) {
    if (vars && typeof vars.count === 'number') {
      const category = plurals.select(vars.count);
      const plural = messages[`${key}.${category}`] ?? messages[`${key}.other`];
      if (plural !== undefined) return plural;
    }
    return messages[key] ?? key;
  }

  return function t(key, vars) {
    const template = pick(key, vars);
    if (!vars) return template;
    return template.replace(/\{(\w+)\}/g, (match, name) => {
      if (!(name in vars)) return match;
      const value = vars[name];
      return typeof value === 'number' ? numbers.format(value) : String(value);
    });
  };
}
'''

FILES[FRONT / "lib/i18n/server.js"] = r'''import { cache } from 'react';
import { cookies, headers } from 'next/headers';
import { DEFAULT_LOCALE, LOCALE_COOKIE, isLocale } from './config';
import { createT } from './translate';
import en from './dictionaries/en';
import ar from './dictionaries/ar';

const DICTIONARIES = { en, ar };

/** Saved choice first, then the browser language, then English. Crawlers get English. */
export const getLocale = cache(async () => {
  const jar = await cookies();
  const saved = jar.get(LOCALE_COOKIE)?.value;
  if (isLocale(saved)) return saved;

  const accept = (await headers()).get('accept-language') || '';
  return /^\s*ar\b/i.test(accept) ? 'ar' : DEFAULT_LOCALE;
});

/** English fills any key the other language does not have. */
export function messagesFor(locale) {
  return { ...en, ...(DICTIONARIES[locale] || {}) };
}

export const getT = cache(async () => {
  const locale = await getLocale();
  return createT(locale, messagesFor(locale));
});
'''

FILES[FRONT / "lib/i18n/dictionaries/en.js"] = r'''const en = {
  // layout
  'skip': 'Skip to content',
  'nav.main': 'Main',
  'nav.remote': 'Remote jobs',
  'nav.today': 'New today',
  'brand.home': '{name} home',
  'brand.tagline': 'Every job. One search.',
  'brand.description': '{name} searches job openings collected from many platforms in one place. Filter by location, company, remote and date, then apply on the original site.',
  'meta.defaultTitle': '{name}: {tagline} Search jobs from every platform',
  'footer.text': '© {year} {name}. Listings are collected from public sources and licensed data providers; you apply on the original site.',
  'lang.label': 'العربية',
  'lang.aria': 'Switch the site language to Arabic',
  'theme.toggle': 'Switch between light and dark theme',

  // home
  'home.eyebrow': 'Job search engine',
  'home.title1': 'Find your next role.',
  'home.title2': 'Every platform, one search.',
  'home.sub': 'Search openings collected from many job platforms, filter them like a pro, and apply on the original site.',
  'home.trending': 'Trending:',
  'home.popular': 'Popular searches',
  'stats.label': 'Database statistics',
  'stats.jobs': 'jobs',
  'stats.companies': 'companies',
  'stats.platforms': 'platforms',
  'platforms.title': 'Platforms we search',
  'platforms.none': 'No jobs collected yet',
  'results.found.one': '{count} job found',
  'results.found.other': '{count} jobs found',
  'results.jobs': 'Jobs',
  'sort.label': 'Sort results',
  'sort.best': 'Best match',
  'sort.newest': 'Newest',
  'error.title': 'We couldn’t load jobs right now',
  'error.text': 'The search service isn’t responding. Please try again in a moment.',
  'error.retry': 'Try again',
  'empty.title': 'No jobs match your search',
  'empty.text': 'Try fewer words, check the spelling, or remove a filter.',
  'empty.clear': 'Clear all filters',

  // filters
  'filters.title': 'Filters',
  'filters.date': 'Date posted',
  'filters.any': 'Any time',
  'filters.24h': 'Past 24 hours',
  'filters.7d': 'Past 7 days',
  'filters.30d': 'Past 30 days',
  'filters.type': 'Work type',
  'filters.remoteOnly': 'Remote only',
  'filters.platform': 'Platform',
  'filters.location': 'Location',
  'filters.company': 'Company',
  'active.label': 'Active filters',
  'active.search': 'Search',
  'active.type': 'Work type',
  'active.location': 'Location',
  'active.company': 'Company',
  'active.platform': 'Platform',
  'active.posted': 'Posted',
  'active.remote': 'Remote',
  'active.remove': ' (remove filter)',
  'active.clearAll': 'Clear all',

  // job card, pager
  'job.new': 'New',
  'job.remote': 'Remote',
  'job.srLink': ' at {company} (opens in a new tab)',
  'job.tags': 'Skills and categories',
  'pager.label': 'Pagination',
  'pager.prev': '← Previous',
  'pager.next': 'Next →',
  'pager.page': 'Page {n}',

  // search box
  'search.placeholder': 'Job title, company or location',
  'search.aria': 'Search jobs by title, company or location',
  'search.go': 'Search',
  'search.busy': 'Searching',
  'search.clear': 'Clear search text',
  'search.suggestions': 'Search suggestions',
  'search.groupJobs': 'Jobs',
  'search.groupCompanies': 'Companies',
  'search.groupLocations': 'Locations',
  'search.groupRecent': 'Recent searches',
  'search.groupTrending': 'Trending',
  'search.removeRecent': 'Remove {label} from recent searches',
  'search.removeTitle': 'Remove from recent searches',
  'search.clearRecent': 'Clear recent searches',

  // account menu and headings
  'menu.login': 'Log in',
  'menu.signup': 'Sign up',
  'menu.account': 'Account menu',
  'menu.password': 'Change password',
  'menu.logout': 'Log out',
  'headline.jobs': 'Jobs',
  'headline.withQuery': '{q} jobs',
  'headline.remote': 'Remote {x}',
  'headline.at': '{x} at {company}',
  'headline.in': '{x} in {location}',
  'headline.on': '{x} on {source}',
  'meta.page': '{title} (page {page})',
  'meta.searchDesc': 'Browse {title} collected from multiple job platforms. Filter by location, company and date posted, then apply on the original site.',
  'meta.login.title': 'Log in',
  'meta.login.desc': 'Log in to your account.',
  'meta.register.title': 'Create your account',
  'meta.register.desc': 'Create a free account.',
  'meta.password.title': 'Change password',
  'meta.password.desc': 'Change your account password.',

  // auth
  'auth.show': 'Show',
  'auth.hide': 'Hide',
  'auth.passwordSr': ' password',
  'auth.email': 'Email',
  'auth.password': 'Password',
  'auth.pwHint': 'At least 8 characters, with letters and numbers.',
  'login.title': 'Welcome back',
  'login.lead': 'Log in to continue.',
  'login.footer': 'New here?',
  'login.footerLink': 'Create an account',
  'login.submit': 'Log in',
  'login.pending': 'Logging in...',
  'register.title': 'Create your account',
  'register.lead': 'It only takes a minute.',
  'register.footer': 'Already have an account?',
  'register.footerLink': 'Log in',
  'register.name': 'Full name',
  'register.confirm': 'Confirm password',
  'register.submit': 'Create account',
  'register.pending': 'Creating account...',
  'pw.title': 'Change password',
  'pw.lead': 'Signed in as {email}.',
  'pw.current': 'Current password',
  'pw.new': 'New password',
  'pw.confirm': 'Confirm new password',
  'pw.submit': 'Update password',
  'pw.pending': 'Updating...',
  'pw.updated': 'Your password was updated. Other devices were signed out.',
  'err.network': 'We could not reach the server. Please try again in a moment.',
  'err.tooMany': 'Too many attempts. Please wait a minute and try again.',
  'err.generic': 'Something went wrong. Please try again.',

  // chatbot
  'chat.open': 'Open job assistant',
  'chat.close': 'Close job assistant',
  'chat.closeBtn': 'Close chat',
  'chat.dialog': 'Job search assistant',
  'chat.title': 'Job assistant',
  'chat.powered': 'Powered by OpenAI',
  'chat.new': 'New',
  'chat.newTitle': 'Start a new chat',
  'chat.disconnect': 'Disconnect',
  'chat.disconnectTitle': 'Remove your API key from this browser',
  'chat.loading': 'Loading...',
  'chat.welcome': 'Hi! Tell me what kind of job you want and I will find the best matches.',
  'chat.s1': 'Remote Python jobs',
  'chat.s2': 'Odoo developer jobs',
  'chat.s3': 'Senior data analyst in Berlin',
  'chat.s4': 'Jobs posted this week',
  'chat.connectTitle': 'Connect your OpenAI API key',
  'chat.connectText': 'The assistant uses OpenAI to understand your request. Paste your own API key to continue; usage is billed to your OpenAI account. The key is encrypted in a secure cookie, never saved in our database, and you can disconnect at any time.',
  'chat.keyLabel': 'OpenAI API key',
  'chat.keyPlaceholder': 'sk-...',
  'chat.connecting': 'Checking your key...',
  'chat.connect': 'Connect and continue',
  'chat.getKey': 'Get an API key from OpenAI →',
  'chat.input': 'Describe the job you want...',
  'chat.inputLabel': 'Your message',
  'chat.send': 'Send message',
  'chat.typing': 'The assistant is typing',
  'chat.suggestions': 'Suggestions',
  'chat.followups': 'Follow-up suggestions',
  'chat.keyword': 'AI index unavailable, so I used keyword search.',
  'chat.openSearch': 'Open full search →',
  'chat.match': '{n}% match',
  'chat.errReach': 'Sorry, I could not reach the search service. Please try again in a moment.',
  'chat.errGeneric': 'Sorry, something went wrong. Please try again.',
  'chat.needKey': 'Please connect your OpenAI API key.',
  'chat.connectFail': 'Could not connect. Please try again.',
  'chat.connectNet': 'Could not reach the server. Please try again.',

  // server messages (chat key and message routes)
  'key.forbidden': 'Forbidden.',
  'key.format': 'That does not look like an OpenAI API key. It should start with "sk-".',
  'key.rejected': 'OpenAI rejected this key. Check it and try again.',
  'key.reach': 'Could not reach OpenAI to verify the key. Please try again.',
  'key.quota': 'This OpenAI account has no remaining credit. Add billing credit in your OpenAI account, then try again.',
  'key.rate': 'OpenAI is rate limiting this key. Try again in a moment.',
  'key.model': 'This key cannot use the required model.',
  'key.modelDetail': ' OpenAI says: {detail}',
  'key.verify': 'OpenAI could not verify the key right now. Try again in a moment.',
  'key.secret': 'The server is missing CHAT_COOKIE_SECRET. Add it to jobs-frontend/.env.local and restart.',
  'msg.needKey': 'Please connect your OpenAI API key to chat.',
  'msg.empty': 'Please type a message.',
  'msg.unreachable': 'The search service is not reachable right now.',
};

export default en;
'''

FILES[FRONT / "lib/i18n/dictionaries/ar.js"] = r'''const ar = {
  // layout
  'skip': 'تخطَّ إلى المحتوى',
  'nav.main': 'التنقل الرئيسي',
  'nav.remote': 'وظائف عن بُعد',
  'nav.today': 'جديد اليوم',
  'brand.home': 'الصفحة الرئيسية لـ {name}',
  'brand.tagline': 'كل الوظائف. بحث واحد.',
  'brand.description': '{name} يبحث في فرص العمل المجمّعة من منصات عديدة في مكان واحد. صفِّ النتائج حسب الموقع والشركة والعمل عن بُعد وتاريخ النشر، ثم قدّم على الموقع الأصلي.',
  'meta.defaultTitle': '{name}: {tagline} ابحث عن وظائف من كل المنصات',
  'footer.text': '© {year} {name}. يتم جمع الوظائف من مصادر عامة ومزوّدي بيانات مرخّصين، ويكون التقديم على الموقع الأصلي.',
  'lang.label': 'English',
  'lang.aria': 'تغيير لغة الموقع إلى الإنجليزية',
  'theme.toggle': 'التبديل بين المظهر الفاتح والداكن',

  // home
  'home.eyebrow': 'محرك البحث عن الوظائف',
  'home.title1': 'اعثر على وظيفتك القادمة.',
  'home.title2': 'كل المنصات في بحث واحد.',
  'home.sub': 'ابحث في الوظائف المجمّعة من منصات توظيف متعددة، وصفِّها باحترافية، ثم قدّم على الموقع الأصلي.',
  'home.trending': 'الأكثر بحثًا:',
  'home.popular': 'عمليات البحث الشائعة',
  'stats.label': 'إحصاءات قاعدة البيانات',
  'stats.jobs': 'وظيفة',
  'stats.companies': 'شركة',
  'stats.platforms': 'منصة',
  'platforms.title': 'المنصات التي نبحث فيها',
  'platforms.none': 'لم يتم جمع وظائف بعد',
  'results.found.zero': 'لم يتم العثور على وظائف',
  'results.found.one': 'تم العثور على وظيفة واحدة',
  'results.found.two': 'تم العثور على وظيفتين',
  'results.found.few': 'تم العثور على {count} وظائف',
  'results.found.many': 'تم العثور على {count} وظيفة',
  'results.found.other': 'تم العثور على {count} وظيفة',
  'results.jobs': 'الوظائف',
  'sort.label': 'ترتيب النتائج',
  'sort.best': 'الأكثر ملاءمة',
  'sort.newest': 'الأحدث',
  'error.title': 'تعذّر تحميل الوظائف حاليًا',
  'error.text': 'خدمة البحث لا تستجيب. يرجى المحاولة مرة أخرى بعد قليل.',
  'error.retry': 'حاول مرة أخرى',
  'empty.title': 'لا توجد وظائف مطابقة لبحثك',
  'empty.text': 'جرّب كلمات أقل، أو تحقق من الإملاء، أو أزل أحد عوامل التصفية.',
  'empty.clear': 'مسح كل عوامل التصفية',

  // filters
  'filters.title': 'عوامل التصفية',
  'filters.date': 'تاريخ النشر',
  'filters.any': 'أي وقت',
  'filters.24h': 'آخر 24 ساعة',
  'filters.7d': 'آخر 7 أيام',
  'filters.30d': 'آخر 30 يومًا',
  'filters.type': 'نوع العمل',
  'filters.remoteOnly': 'عن بُعد فقط',
  'filters.platform': 'المنصة',
  'filters.location': 'الموقع',
  'filters.company': 'الشركة',
  'active.label': 'عوامل التصفية النشطة',
  'active.search': 'البحث',
  'active.type': 'نوع العمل',
  'active.location': 'الموقع',
  'active.company': 'الشركة',
  'active.platform': 'المنصة',
  'active.posted': 'النشر',
  'active.remote': 'عن بُعد',
  'active.remove': ' (إزالة عامل التصفية)',
  'active.clearAll': 'مسح الكل',

  // job card, pager
  'job.new': 'جديد',
  'job.remote': 'عن بُعد',
  'job.srLink': ' لدى {company} (يفتح في علامة تبويب جديدة)',
  'job.tags': 'المهارات والتصنيفات',
  'pager.label': 'التنقل بين الصفحات',
  'pager.prev': '→ السابق',
  'pager.next': 'التالي ←',
  'pager.page': 'الصفحة {n}',

  // search box
  'search.placeholder': 'المسمى الوظيفي أو الشركة أو الموقع',
  'search.aria': 'ابحث عن وظائف بالمسمى الوظيفي أو الشركة أو الموقع',
  'search.go': 'بحث',
  'search.busy': 'جارٍ البحث',
  'search.clear': 'مسح نص البحث',
  'search.suggestions': 'اقتراحات البحث',
  'search.groupJobs': 'وظائف',
  'search.groupCompanies': 'شركات',
  'search.groupLocations': 'مواقع',
  'search.groupRecent': 'عمليات البحث الأخيرة',
  'search.groupTrending': 'الأكثر بحثًا',
  'search.removeRecent': 'إزالة {label} من عمليات البحث الأخيرة',
  'search.removeTitle': 'إزالة من عمليات البحث الأخيرة',
  'search.clearRecent': 'مسح عمليات البحث الأخيرة',

  // account menu and headings
  'menu.login': 'تسجيل الدخول',
  'menu.signup': 'إنشاء حساب',
  'menu.account': 'قائمة الحساب',
  'menu.password': 'تغيير كلمة المرور',
  'menu.logout': 'تسجيل الخروج',
  'headline.jobs': 'وظائف',
  'headline.withQuery': 'وظائف {q}',
  'headline.remote': '{x} عن بُعد',
  'headline.at': '{x} لدى {company}',
  'headline.in': '{x} في {location}',
  'headline.on': '{x} على {source}',
  'meta.page': '{title} (الصفحة {page})',
  'meta.searchDesc': 'تصفّح {title} المجمّعة من منصات توظيف متعددة. صفِّ النتائج حسب الموقع والشركة وتاريخ النشر، ثم قدّم على الموقع الأصلي.',
  'meta.login.title': 'تسجيل الدخول',
  'meta.login.desc': 'سجّل الدخول إلى حسابك.',
  'meta.register.title': 'إنشاء حسابك',
  'meta.register.desc': 'أنشئ حسابًا مجانيًا.',
  'meta.password.title': 'تغيير كلمة المرور',
  'meta.password.desc': 'غيّر كلمة مرور حسابك.',

  // auth
  'auth.show': 'إظهار',
  'auth.hide': 'إخفاء',
  'auth.passwordSr': ' كلمة المرور',
  'auth.email': 'البريد الإلكتروني',
  'auth.password': 'كلمة المرور',
  'auth.pwHint': 'ثمانية أحرف على الأقل، تتضمن حروفًا وأرقامًا.',
  'login.title': 'مرحبًا بعودتك',
  'login.lead': 'سجّل الدخول للمتابعة.',
  'login.footer': 'مستخدم جديد؟',
  'login.footerLink': 'أنشئ حسابًا',
  'login.submit': 'تسجيل الدخول',
  'login.pending': 'جارٍ تسجيل الدخول...',
  'register.title': 'أنشئ حسابك',
  'register.lead': 'يستغرق الأمر دقيقة واحدة فقط.',
  'register.footer': 'لديك حساب بالفعل؟',
  'register.footerLink': 'سجّل الدخول',
  'register.name': 'الاسم الكامل',
  'register.confirm': 'تأكيد كلمة المرور',
  'register.submit': 'إنشاء الحساب',
  'register.pending': 'جارٍ إنشاء الحساب...',
  'pw.title': 'تغيير كلمة المرور',
  'pw.lead': 'تم تسجيل الدخول باسم {email}.',
  'pw.current': 'كلمة المرور الحالية',
  'pw.new': 'كلمة المرور الجديدة',
  'pw.confirm': 'تأكيد كلمة المرور الجديدة',
  'pw.submit': 'تحديث كلمة المرور',
  'pw.pending': 'جارٍ التحديث...',
  'pw.updated': 'تم تحديث كلمة المرور. تم تسجيل الخروج من الأجهزة الأخرى.',
  'err.network': 'تعذّر الوصول إلى الخادم. يرجى المحاولة مرة أخرى بعد قليل.',
  'err.tooMany': 'محاولات كثيرة. يرجى الانتظار دقيقة ثم المحاولة مرة أخرى.',
  'err.generic': 'حدث خطأ ما. يرجى المحاولة مرة أخرى.',

  // chatbot
  'chat.open': 'فتح مساعد الوظائف',
  'chat.close': 'إغلاق مساعد الوظائف',
  'chat.closeBtn': 'إغلاق المحادثة',
  'chat.dialog': 'مساعد البحث عن الوظائف',
  'chat.title': 'مساعد الوظائف',
  'chat.powered': 'مدعوم من OpenAI',
  'chat.new': 'جديد',
  'chat.newTitle': 'بدء محادثة جديدة',
  'chat.disconnect': 'فصل',
  'chat.disconnectTitle': 'إزالة مفتاح API من هذا المتصفح',
  'chat.loading': 'جارٍ التحميل...',
  'chat.welcome': 'مرحبًا! أخبرني بنوع الوظيفة التي تريدها وسأجد لك أفضل النتائج.',
  'chat.s1': 'وظائف Python عن بُعد',
  'chat.s2': 'وظائف مطوّر Odoo',
  'chat.s3': 'محلل بيانات خبير في برلين',
  'chat.s4': 'وظائف نُشرت هذا الأسبوع',
  'chat.connectTitle': 'اربط مفتاح OpenAI API الخاص بك',
  'chat.connectText': 'يستخدم المساعد OpenAI لفهم طلبك. الصق مفتاح API الخاص بك للمتابعة؛ تُحاسَب الاستخدامات على حسابك في OpenAI. يتم تشفير المفتاح في ملف تعريف ارتباط آمن ولا يُحفظ في قاعدة بياناتنا، ويمكنك فصله في أي وقت.',
  'chat.keyLabel': 'مفتاح OpenAI API',
  'chat.keyPlaceholder': 'sk-...',
  'chat.connecting': 'جارٍ التحقق من المفتاح...',
  'chat.connect': 'اربط وتابع',
  'chat.getKey': 'احصل على مفتاح API من OpenAI ←',
  'chat.input': 'صِف الوظيفة التي تريدها...',
  'chat.inputLabel': 'رسالتك',
  'chat.send': 'إرسال الرسالة',
  'chat.typing': 'المساعد يكتب',
  'chat.suggestions': 'اقتراحات',
  'chat.followups': 'اقتراحات للمتابعة',
  'chat.keyword': 'فهرس الذكاء الاصطناعي غير متاح، لذلك استخدمت البحث بالكلمات المفتاحية.',
  'chat.openSearch': 'افتح البحث الكامل ←',
  'chat.match': 'تطابق {n}%',
  'chat.errReach': 'عذرًا، تعذّر الوصول إلى خدمة البحث. يرجى المحاولة مرة أخرى بعد قليل.',
  'chat.errGeneric': 'عذرًا، حدث خطأ ما. يرجى المحاولة مرة أخرى.',
  'chat.needKey': 'يرجى ربط مفتاح OpenAI API الخاص بك.',
  'chat.connectFail': 'تعذّر الاتصال. يرجى المحاولة مرة أخرى.',
  'chat.connectNet': 'تعذّر الوصول إلى الخادم. يرجى المحاولة مرة أخرى.',

  // server messages (chat key and message routes)
  'key.forbidden': 'ممنوع.',
  'key.format': 'هذا لا يبدو مفتاح OpenAI API. يجب أن يبدأ بـ "sk-".',
  'key.rejected': 'رفضت OpenAI هذا المفتاح. تحقق منه وحاول مرة أخرى.',
  'key.reach': 'تعذّر الوصول إلى OpenAI للتحقق من المفتاح. يرجى المحاولة مرة أخرى.',
  'key.quota': 'لا يوجد رصيد متبقٍ في حساب OpenAI هذا. أضف رصيدًا في حسابك ثم حاول مرة أخرى.',
  'key.rate': 'تقوم OpenAI بتقييد معدل الطلبات لهذا المفتاح. حاول بعد قليل.',
  'key.model': 'لا يمكن لهذا المفتاح استخدام النموذج المطلوب.',
  'key.modelDetail': ' تقول OpenAI: {detail}',
  'key.verify': 'تعذّر على OpenAI التحقق من المفتاح الآن. حاول مرة أخرى بعد قليل.',
  'key.secret': 'الخادم يفتقد CHAT_COOKIE_SECRET. أضفه إلى jobs-frontend/.env.local ثم أعد التشغيل.',
  'msg.needKey': 'يرجى ربط مفتاح OpenAI API للدردشة.',
  'msg.empty': 'يرجى كتابة رسالة.',
  'msg.unreachable': 'خدمة البحث غير متاحة حاليًا.',
};

export default ar;
'''

FILES[FRONT / "app/i18n-actions.js"] = r'''"use server";

import { cookies } from 'next/headers';
import { revalidatePath } from 'next/cache';
import { LOCALE_COOKIE, isLocale } from '../lib/i18n/config';

export async function setLocaleAction(formData) {
  const locale = String(formData.get('locale') ?? '');
  if (!isLocale(locale)) return;

  const jar = await cookies();
  jar.set(LOCALE_COOKIE, locale, {
    httpOnly: true,
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
    path: '/',
    maxAge: 60 * 60 * 24 * 365,
  });

  // Re-render every server component with the new language.
  revalidatePath('/', 'layout');
}
'''

FILES[FRONT / "components/I18nProvider.js"] = r'''"use client";

import { createContext, useContext, useMemo } from 'react';
import { createT } from '../lib/i18n/translate';

const Context = createContext(null);

export function I18nProvider({ locale, messages, children }) {
  const value = useMemo(() => ({ locale, t: createT(locale, messages) }), [locale, messages]);
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useI18n() {
  const value = useContext(Context);
  if (!value) throw new Error('useI18n must be used inside <I18nProvider>.');
  return value;
}

export function useT() {
  return useI18n().t;
}
'''

FILES[FRONT / "components/LanguageToggle.js"] = r'''import { getLocale, getT } from '../lib/i18n/server';
import { setLocaleAction } from '../app/i18n-actions';

function GlobeIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18M12 3c2.6 2.6 4 5.7 4 9s-1.4 6.4-4 9c-2.6-2.6-4-5.7-4-9s1.4-6.4 4-9Z" />
    </svg>
  );
}

export default async function LanguageToggle() {
  const locale = await getLocale();
  const t = await getT();
  const target = locale === 'ar' ? 'en' : 'ar';

  return (
    <form action={setLocaleAction}>
      <input type="hidden" name="locale" value={target} />
      <button type="submit" className="icon-btn lang-btn" aria-label={t('lang.aria')} title={t('lang.aria')} lang={target}>
        <GlobeIcon />
        <span>{t('lang.label')}</span>
      </button>
    </form>
  );
}
'''

FILES[FRONT / "components/ThemeToggle.js"] = r'''"use client";

import { useT } from './I18nProvider';

const COOKIE = 'hirelume_theme';

function SunIcon() {
  return (
    <svg className="ti-sun" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg className="ti-moon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" />
    </svg>
  );
}

/** Sun shows in dark mode (click for light), moon shows in light mode (click for dark). CSS picks the icon. */
export default function ThemeToggle() {
  const t = useT();

  function toggle() {
    const root = document.documentElement;
    const current =
      root.dataset.theme || (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
    const next = current === 'light' ? 'dark' : 'light';
    root.dataset.theme = next;
    document.cookie = `${COOKIE}=${next}; path=/; max-age=31536000; samesite=lax`;
  }

  return (
    <button type="button" className="icon-btn theme-btn" onClick={toggle} aria-label={t('theme.toggle')} title={t('theme.toggle')}>
      <SunIcon />
      <MoonIcon />
    </button>
  );
}
'''

# =====================================================================
# FRONTEND: shared libs
# =====================================================================

FILES[FRONT / "lib/auth.js"] = r'''import { cache } from 'react';
import { cookies } from 'next/headers';
import { getLocale } from './i18n/server';

export const SESSION_COOKIE = 'hirelume_session';
const API = process.env.API_INTERNAL_URL || 'http://127.0.0.1:8000/api';
const MONTH = 60 * 60 * 24 * 30;

/** Call the Laravel API from the server. Never throws. Sends the site language for validation messages. */
export async function api(path, { method = 'GET', body, token } = {}) {
  const headers = { Accept: 'application/json', 'X-Locale': await getLocale() };
  if (body) headers['Content-Type'] = 'application/json';
  if (token) headers.Authorization = `Bearer ${token}`;

  try {
    const res = await fetch(`${API}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      cache: 'no-store',
    });
    let data = null;
    try {
      data = await res.json();
    } catch {}
    return { ok: res.ok, status: res.status, data };
  } catch {
    return { ok: false, status: 0, data: null };
  }
}

export async function getToken() {
  const jar = await cookies();
  return jar.get(SESSION_COOKIE)?.value ?? null;
}

export async function setSession(token) {
  const jar = await cookies();
  jar.set(SESSION_COOKIE, token, {
    httpOnly: true,
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
    path: '/',
    maxAge: MONTH,
  });
}

/** The signed-in user, or null. Cached for the duration of one request. */
export const getUser = cache(async () => {
  const token = await getToken();
  if (!token) return null;
  const res = await api('/auth/me', { token });
  return res.ok ? res.data?.user ?? null : null;
});
'''

FILES[FRONT / "lib/params.js"] = r'''import { platformLabel } from './platforms';

export const FILTER_KEYS = ['q', 'source', 'location', 'company', 'posted', 'remote', 'sort'];

const one = (v) => (Array.isArray(v) ? v[0] : v) || '';

export function normalize(sp = {}) {
  const page = parseInt(one(sp.page), 10);
  const sort = one(sp.sort);
  const posted = one(sp.posted);

  return {
    q: one(sp.q).trim().slice(0, 100),
    source: one(sp.source).slice(0, 100),
    location: one(sp.location).slice(0, 150),
    company: one(sp.company).slice(0, 255),
    posted: ['24h', '7d', '30d'].includes(posted) ? posted : '',
    remote: one(sp.remote) === '1' ? '1' : '',
    sort: sort === 'newest' || sort === 'relevance' ? sort : '',
    page: Number.isFinite(page) && page > 1 ? page : 1,
  };
}

/** Build a crawlable URL. Any change resets to page 1 unless a page is given. */
export function buildHref(params, overrides = {}) {
  const merged = { ...params, ...overrides };
  if (!('page' in overrides)) merged.page = 1;

  const usp = new URLSearchParams();
  for (const key of FILTER_KEYS) {
    if (merged[key]) usp.set(key, merged[key]);
  }
  if (merged.page > 1) usp.set('page', String(merged.page));

  const qs = usp.toString();
  return qs ? `/?${qs}` : '/';
}

export function hasFilters(p) {
  return Boolean(p.q || p.source || p.location || p.company || p.posted || p.remote);
}

/** Page heading in the current language, for example "Remote Python jobs in Berlin on LinkedIn". */
export function headline(p, t) {
  let text = p.q ? t('headline.withQuery', { q: p.q }) : t('headline.jobs');
  if (p.remote) text = t('headline.remote', { x: text });
  if (p.company) text = t('headline.at', { x: text, company: p.company });
  if (p.location) text = t('headline.in', { x: text, location: p.location });
  if (p.source) text = t('headline.on', { x: text, source: platformLabel(p.source) });
  return text;
}
'''

# =====================================================================
# FRONTEND: layout and home page
# =====================================================================

FILES[FRONT / "app/layout.js"] = r'''import './globals.css';
import Link from 'next/link';
import { cookies } from 'next/headers';
import { Inter, Space_Grotesk, Noto_Sans_Arabic } from 'next/font/google';
import { BRAND } from '../lib/brand';
import { DIRECTION, THEME_COOKIE } from '../lib/i18n/config';
import { getLocale, getT, messagesFor } from '../lib/i18n/server';
import { I18nProvider } from '../components/I18nProvider';
import { LogoMark } from '../components/Logo';
import UserMenu from '../components/UserMenu';
import ChatWidget from '../components/chat/ChatWidget';
import LanguageToggle from '../components/LanguageToggle';
import ThemeToggle from '../components/ThemeToggle';

const body = Inter({ subsets: ['latin'], variable: '--font-body', display: 'swap' });
const display = Space_Grotesk({ subsets: ['latin'], variable: '--font-display', display: 'swap' });
// Loaded only when Arabic text is actually shown.
const arabic = Noto_Sans_Arabic({ subsets: ['arabic'], variable: '--font-ar', display: 'swap', preload: false });

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000';

export async function generateMetadata() {
  const t = await getT();
  const title = t('meta.defaultTitle', { name: BRAND.name, tagline: t('brand.tagline') });
  const description = t('brand.description', { name: BRAND.name });

  return {
    metadataBase: new URL(SITE_URL),
    title: { default: title, template: `%s | ${BRAND.name}` },
    description,
    applicationName: BRAND.name,
    openGraph: { type: 'website', siteName: BRAND.name, title, description, url: '/' },
    twitter: { card: 'summary_large_image' },
    robots: { index: true, follow: true },
  };
}

export const viewport = {
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#f4f6ff' },
    { media: '(prefers-color-scheme: dark)', color: '#080c1a' },
  ],
  colorScheme: 'dark light',
};

export default async function RootLayout({ children }) {
  const locale = await getLocale();
  const t = await getT();
  const jar = await cookies();
  const savedTheme = jar.get(THEME_COOKIE)?.value;
  const theme = savedTheme === 'light' || savedTheme === 'dark' ? savedTheme : undefined;

  const organization = {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: BRAND.name,
    url: SITE_URL,
    logo: `${SITE_URL}/icon.svg`,
    description: t('brand.description', { name: BRAND.name }),
  };

  return (
    <html lang={locale} dir={DIRECTION[locale]} data-theme={theme}>
      <body className={`${body.variable} ${display.variable} ${arabic.variable}`}>
        <I18nProvider locale={locale} messages={messagesFor(locale)}>
          <script
            type="application/ld+json"
            dangerouslySetInnerHTML={{ __html: JSON.stringify(organization).replace(/</g, '\\u003c') }}
          />
          <a className="skip" href="#main">{t('skip')}</a>

          <header className="site-header">
            <div className="wrap">
              <Link href="/" className="brand" aria-label={t('brand.home', { name: BRAND.name })}>
                <span className="brand-mark"><LogoMark /></span>
                <span>{BRAND.parts[0]}<b>{BRAND.parts[1]}</b></span>
              </Link>
              <nav className="nav" aria-label={t('nav.main')}>
                <Link href="/?remote=1" prefetch={false}>{t('nav.remote')}</Link>
                <Link href="/?posted=24h" prefetch={false}>{t('nav.today')}</Link>
              </nav>
              <div className="header-right">
                <LanguageToggle />
                <ThemeToggle />
                <UserMenu />
              </div>
            </div>
          </header>

          {children}

          <ChatWidget />

          <footer className="site-footer">
            <div className="wrap">
              <p>{t('footer.text', { year: String(new Date().getFullYear()), name: BRAND.name })}</p>
            </div>
          </footer>
        </I18nProvider>
      </body>
    </html>
  );
}
'''

FILES[FRONT / "app/page.js"] = r'''import Link from 'next/link';
import { getJobs, getStats } from '../lib/server-api';
import { normalize, buildHref, headline, hasFilters } from '../lib/params';
import { TRENDING } from '../lib/trending';
import { BRAND } from '../lib/brand';
import { PLATFORMS } from '../lib/platforms';
import { INTL } from '../lib/i18n/config';
import { getLocale, getT } from '../lib/i18n/server';
import SearchPanel from '../components/SearchPanel';
import FiltersToggle from '../components/FiltersToggle';
import FilterSidebar from '../components/FilterSidebar';
import ActiveFilters from '../components/ActiveFilters';
import JobCard from '../components/JobCard';
import Pagination from '../components/Pagination';

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000';

export async function generateMetadata({ searchParams }) {
  const p = normalize(await searchParams);

  if (!hasFilters(p) && p.page === 1 && !p.sort) {
    return { alternates: { canonical: '/' } };
  }

  const t = await getT();

  // Index search pages with at most one facet; keep the rest out of the index.
  const facetCount = [p.location, p.company, p.source, p.remote].filter(Boolean).length;
  const noindex = p.page > 1 || Boolean(p.sort) || Boolean(p.posted) || facetCount > 1;

  const canonical = buildHref({
    q: p.q, location: p.location, company: p.company, source: p.source, remote: p.remote,
  });
  const base = headline(p, t);
  const title = p.page > 1 ? t('meta.page', { title: base, page: String(p.page) }) : base;
  const description = t('meta.searchDesc', { title: base.toLowerCase() });

  return {
    title,
    description,
    alternates: { canonical },
    robots: { index: !noindex, follow: true },
    openGraph: { title, description, url: canonical, type: 'website' },
  };
}

export default async function Home({ searchParams }) {
  const p = normalize(await searchParams);
  const locale = await getLocale();
  const t = await getT();
  const nf = new Intl.NumberFormat(INTL[locale]);

  let stats = null;
  let data = null;
  let failed = false;

  try {
    [stats, data] = await Promise.all([getStats(), getJobs(p)]);
  } catch {
    failed = true;
  }

  const facets = {
    sources: data?.facets?.sources ?? (stats?.by_source ?? []).map((s) => ({ key: s.name, count: s.count })),
    locations: data?.facets?.locations ?? [],
    companies: data?.facets?.companies ?? [],
    posted: data?.facets?.posted ?? {},
    remote: data?.facets?.remote ?? 0,
  };

  const total = data?.total ?? 0;
  const jobs = data?.data ?? [];
  const filtered = hasFilters(p);
  const activeCount = [p.location, p.company, p.source, p.posted, p.remote].filter(Boolean).length;
  const counts = Object.fromEntries((stats?.by_source ?? []).map((s) => [s.name, s.count]));
  const effectiveSort = p.sort || (p.q ? 'relevance' : 'newest');
  const perPage = data?.per_page ?? 12;

  const jsonLd = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'WebSite',
        '@id': `${SITE_URL}/#website`,
        url: SITE_URL,
        name: BRAND.name,
        potentialAction: {
          '@type': 'SearchAction',
          target: { '@type': 'EntryPoint', urlTemplate: `${SITE_URL}/?q={search_term_string}` },
          'query-input': 'required name=search_term_string',
        },
      },
      ...(jobs.length
        ? [{
            '@type': 'ItemList',
            itemListElement: jobs.map((j, i) => ({
              '@type': 'ListItem',
              position: (p.page - 1) * perPage + i + 1,
              url: j.url,
              name: `${j.title} - ${j.company}`,
            })),
          }]
        : []),
    ],
  };

  return (
    <main id="main">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, '\\u003c') }}
      />

      <section className="hero wrap" aria-labelledby="page-title">
        <p className="eyebrow">{t('home.eyebrow')}</p>
        <h1 id="page-title">
          {filtered ? headline(p, t) : <>{t('home.title1')}{' '}<em>{t('home.title2')}</em></>}
        </h1>
        <p className="sub">{t('home.sub')}</p>

        <SearchPanel params={p} />

        <ul className="trending" aria-label={t('home.popular')}>
          <li><span>{t('home.trending')}</span></li>
          {TRENDING.slice(0, 6).map((term) => (
            <li key={term}>
              <Link href={buildHref({}, { q: term })} prefetch={false}>{term}</Link>
            </li>
          ))}
        </ul>

        {stats && (
          <ul className="stats" aria-label={t('stats.label')}>
            <li><strong>{nf.format(stats.total_jobs)}</strong><span>{t('stats.jobs')}</span></li>
            <li><strong>{nf.format(stats.total_companies)}</strong><span>{t('stats.companies')}</span></li>
            <li><strong>{nf.format(stats.by_source.length)}</strong><span>{t('stats.platforms')}</span></li>
          </ul>
        )}
      </section>

      <section className="platforms wrap" aria-labelledby="platforms-title">
        <h2 id="platforms-title">{t('platforms.title')}</h2>
        <ul>
          {PLATFORMS.map((pl) => {
            const n = counts[pl.key] || 0;
            return (
              <li key={pl.key}>
                {n > 0 ? (
                  <Link href={buildHref({}, { source: pl.key })} prefetch={false} className="plat">
                    {pl.label} <em>{nf.format(n)}</em>
                  </Link>
                ) : (
                  <span className="plat off" title={t('platforms.none')}>{pl.label}</span>
                )}
              </li>
            );
          })}
        </ul>
      </section>

      <div id="results" className="results-layout wrap" tabIndex={-1}>
        <FiltersToggle activeCount={activeCount}>
          <FilterSidebar params={p} facets={facets} />
        </FiltersToggle>

        <section className="results-main" aria-labelledby="results-title">
          <div className="results-head">
            <h2 id="results-title">
              {failed ? t('results.jobs') : t('results.found', { count: total })}
            </h2>
            {!failed && total > 0 && (
              <nav className="sort" aria-label={t('sort.label')}>
                {p.q && (
                  <Link
                    href={buildHref(p, { sort: 'relevance' })}
                    aria-current={effectiveSort === 'relevance' ? 'true' : undefined}
                    prefetch={false}
                    scroll={false}
                  >
                    {t('sort.best')}
                  </Link>
                )}
                <Link
                  href={buildHref(p, { sort: 'newest' })}
                  aria-current={effectiveSort === 'newest' ? 'true' : undefined}
                  prefetch={false}
                  scroll={false}
                >
                  {t('sort.newest')}
                </Link>
              </nav>
            )}
          </div>

          <ActiveFilters params={p} />

          {failed && (
            <div className="empty" role="alert">
              <h3>{t('error.title')}</h3>
              <p>{t('error.text')}</p>
              <Link className="btn-link" href={buildHref(p, {})} prefetch={false}>{t('error.retry')}</Link>
            </div>
          )}

          {!failed && total === 0 && (
            <div className="empty">
              <h3>{t('empty.title')}</h3>
              <p>{t('empty.text')}</p>
              <ul className="trending">
                {TRENDING.slice(0, 5).map((term) => (
                  <li key={term}><Link href={buildHref({}, { q: term })} prefetch={false}>{term}</Link></li>
                ))}
              </ul>
              <Link className="btn-link" href="/" prefetch={false}>{t('empty.clear')}</Link>
            </div>
          )}

          {jobs.length > 0 && (
            <div className="grid">
              {jobs.map((job) => <JobCard key={job.id} job={job} />)}
            </div>
          )}

          {data && <Pagination params={p} current={data.current_page} last={data.last_page} />}
        </section>
      </div>
    </main>
  );
}
'''

# =====================================================================
# FRONTEND: components
# =====================================================================

FILES[FRONT / "components/JobCard.js"] = r'''import { INTL } from '../lib/i18n/config';
import { getLocale, getT } from '../lib/i18n/server';
import { platformLabel } from '../lib/platforms';

export default async function JobCard({ job }) {
  const locale = await getLocale();
  const t = await getT();
  const fmt = new Intl.DateTimeFormat(INTL[locale], {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC',
  });

  const posted = job.posted_at ? new Date(job.posted_at) : null;
  const isNew = posted && Date.now() - posted.getTime() < 48 * 3600 * 1000;

  return (
    <article className="card">
      <header className="card-top">
        <span className="badge">{platformLabel(job.source)}</span>
        {isNew && <span className="new">{t('job.new')}</span>}
        {job.remote && <span className="remote">{t('job.remote')}</span>}
        {posted && <time dateTime={posted.toISOString()}>{fmt.format(posted)}</time>}
      </header>

      <h3>
        <a href={job.url} target="_blank" rel="nofollow noopener noreferrer">
          {job.title}
          <span className="sr">{t('job.srLink', { company: job.company })}</span>
        </a>
      </h3>

      <p className="meta">
        {job.company}
        {job.location ? ` · ${job.location}` : ''}
      </p>

      {job.excerpt && <p className="excerpt">{job.excerpt}</p>}

      {job.tags?.length > 0 && (
        <ul className="tags" aria-label={t('job.tags')}>
          {job.tags.map((tag) => <li key={tag} className="tag">{tag}</li>)}
        </ul>
      )}
    </article>
  );
}
'''

FILES[FRONT / "components/Pagination.js"] = r'''import Link from 'next/link';
import { buildHref } from '../lib/params';
import { getT } from '../lib/i18n/server';

function windowPages(current, last) {
  const set = new Set([1, last, current - 2, current - 1, current, current + 1, current + 2]);
  const pages = [...set].filter((n) => n >= 1 && n <= last).sort((a, b) => a - b);
  const out = [];
  pages.forEach((n, i) => {
    if (i && n - pages[i - 1] > 1) out.push(`gap-${n}`);
    out.push(n);
  });
  return out;
}

export default async function Pagination({ params, current, last }) {
  if (last <= 1) return null;
  const t = await getT();

  return (
    <nav className="pager" aria-label={t('pager.label')}>
      {current > 1 ? (
        <Link href={buildHref(params, { page: current - 1 })} rel="prev" prefetch={false}>{t('pager.prev')}</Link>
      ) : (
        <span className="pg" aria-disabled="true">{t('pager.prev')}</span>
      )}

      <ol>
        {windowPages(current, last).map((n) =>
          typeof n === 'number' ? (
            <li key={n}>
              {n === current ? (
                <span className="pg" aria-current="page">{n}</span>
              ) : (
                <Link href={buildHref(params, { page: n })} prefetch={false} aria-label={t('pager.page', { n: String(n) })}>{n}</Link>
              )}
            </li>
          ) : (
            <li key={n} aria-hidden="true"><span className="pg">…</span></li>
          )
        )}
      </ol>

      {current < last ? (
        <Link href={buildHref(params, { page: current + 1 })} rel="next" prefetch={false}>{t('pager.next')}</Link>
      ) : (
        <span className="pg" aria-disabled="true">{t('pager.next')}</span>
      )}
    </nav>
  );
}
'''

FILES[FRONT / "components/FilterSidebar.js"] = r'''import Link from 'next/link';
import { buildHref } from '../lib/params';
import { platformLabel } from '../lib/platforms';
import { INTL } from '../lib/i18n/config';
import { getLocale, getT } from '../lib/i18n/server';

function Option({ href, label, count, selected, nf }) {
  return (
    <li>
      <Link
        href={href}
        className={selected ? 'opt selected' : 'opt'}
        aria-current={selected ? 'true' : undefined}
        prefetch={false}
        scroll={false}
      >
        <span className="box" aria-hidden="true">{selected ? '✓' : ''}</span>
        <span className="opt-label">{label}</span>
        {typeof count === 'number' && <span className="opt-count">{nf.format(count)}</span>}
      </Link>
    </li>
  );
}

function withSelected(list, selected) {
  if (!selected || list.some((i) => i.key === selected)) return list;
  return [{ key: selected, count: undefined }, ...list];
}

export default async function FilterSidebar({ params, facets }) {
  const locale = await getLocale();
  const t = await getT();
  const nf = new Intl.NumberFormat(INTL[locale]);

  const toggle = (key, value) => buildHref(params, { [key]: params[key] === value ? '' : value });
  const sources = withSelected(facets.sources, params.source);
  const locations = withSelected(facets.locations, params.location);
  const companies = withSelected(facets.companies, params.company);
  const posted = [['24h', t('filters.24h')], ['7d', t('filters.7d')], ['30d', t('filters.30d')]];

  return (
    <div className="filters">
      <h2 className="sr">{t('filters.title')}</h2>

      <section aria-labelledby="f-date">
        <h3 id="f-date">{t('filters.date')}</h3>
        <ul>
          <Option href={buildHref(params, { posted: '' })} label={t('filters.any')} selected={!params.posted} nf={nf} />
          {posted.map(([key, label]) => (
            <Option
              key={key}
              href={toggle('posted', key)}
              label={label}
              count={facets.posted?.[key]}
              selected={params.posted === key}
              nf={nf}
            />
          ))}
        </ul>
      </section>

      <section aria-labelledby="f-type">
        <h3 id="f-type">{t('filters.type')}</h3>
        <ul>
          <Option
            href={buildHref(params, { remote: params.remote ? '' : '1' })}
            label={t('filters.remoteOnly')}
            count={facets.remote}
            selected={Boolean(params.remote)}
            nf={nf}
          />
        </ul>
      </section>

      {sources.length > 0 && (
        <section aria-labelledby="f-source">
          <h3 id="f-source">{t('filters.platform')}</h3>
          <ul>
            {sources.map((s) => (
              <Option key={s.key} href={toggle('source', s.key)} label={platformLabel(s.key)} count={s.count} selected={params.source === s.key} nf={nf} />
            ))}
          </ul>
        </section>
      )}

      {locations.length > 0 && (
        <section aria-labelledby="f-location">
          <h3 id="f-location">{t('filters.location')}</h3>
          <ul>
            {locations.map((l) => (
              <Option key={l.key} href={toggle('location', l.key)} label={l.key} count={l.count} selected={params.location === l.key} nf={nf} />
            ))}
          </ul>
        </section>
      )}

      {companies.length > 0 && (
        <section aria-labelledby="f-company">
          <h3 id="f-company">{t('filters.company')}</h3>
          <ul>
            {companies.map((c) => (
              <Option key={c.key} href={toggle('company', c.key)} label={c.key} count={c.count} selected={params.company === c.key} nf={nf} />
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
'''

FILES[FRONT / "components/ActiveFilters.js"] = r'''import Link from 'next/link';
import { buildHref } from '../lib/params';
import { platformLabel } from '../lib/platforms';
import { getT } from '../lib/i18n/server';

export default async function ActiveFilters({ params }) {
  const t = await getT();
  const posted = { '24h': t('filters.24h'), '7d': t('filters.7d'), '30d': t('filters.30d') };

  const chips = [];
  if (params.q) chips.push([t('active.search'), `“${params.q}”`, { q: '' }]);
  if (params.remote) chips.push([t('active.type'), t('active.remote'), { remote: '' }]);
  if (params.location) chips.push([t('active.location'), params.location, { location: '' }]);
  if (params.company) chips.push([t('active.company'), params.company, { company: '' }]);
  if (params.source) chips.push([t('active.platform'), platformLabel(params.source), { source: '' }]);
  if (params.posted) chips.push([t('active.posted'), posted[params.posted], { posted: '' }]);

  if (!chips.length) return null;

  return (
    <div className="active">
      <ul className="active-list" aria-label={t('active.label')}>
        {chips.map(([kind, label, clear]) => (
          <li key={kind}>
            <Link className="chipx" href={buildHref(params, clear)} prefetch={false} scroll={false}>
              <span><span className="sr">{kind}: </span><b>{label}</b></span>
              <span aria-hidden="true">×</span>
              <span className="sr">{t('active.remove')}</span>
            </Link>
          </li>
        ))}
      </ul>
      <Link href="/" className="clear-all" prefetch={false}>{t('active.clearAll')}</Link>
    </div>
  );
}
'''

FILES[FRONT / "components/FiltersToggle.js"] = r'''"use client";

import { useState } from 'react';
import { useT } from './I18nProvider';

export default function FiltersToggle({ activeCount = 0, children }) {
  const t = useT();
  const [open, setOpen] = useState(false);

  return (
    <aside className="filters-wrap" aria-label={t('filters.title')}>
      <button
        type="button"
        className="filters-btn"
        aria-expanded={open}
        aria-controls="filters-panel"
        onClick={() => setOpen(!open)}
      >
        {t('filters.title')}
        {activeCount > 0 && <span className="badge-count">{activeCount}</span>}
      </button>
      <div id="filters-panel" className={open ? 'filters-panel open' : 'filters-panel'}>
        {children}
      </div>
    </aside>
  );
}
'''

FILES[FRONT / "components/UserMenu.js"] = r'''import Link from 'next/link';
import { getUser } from '../lib/auth';
import { getT } from '../lib/i18n/server';
import { logoutAction } from '../app/auth/actions';

export default async function UserMenu() {
  const user = await getUser();
  const t = await getT();

  if (!user) {
    return (
      <div className="auth-links">
        <Link href="/login" className="btn-ghost" prefetch={false}>{t('menu.login')}</Link>
        <Link href="/register" className="btn-solid" prefetch={false}>{t('menu.signup')}</Link>
      </div>
    );
  }

  const initial = (user.name || user.email || '?').trim().charAt(0).toUpperCase();

  return (
    <details className="usermenu">
      <summary aria-label={t('menu.account')}>
        <span className="avatar" aria-hidden="true">{initial}</span>
        <span className="uname">{user.name}</span>
      </summary>
      <div className="usermenu-panel">
        <p className="who">{user.email}</p>
        <Link href="/account/password" prefetch={false}>{t('menu.password')}</Link>
        <form action={logoutAction}>
          <button type="submit">{t('menu.logout')}</button>
        </form>
      </div>
    </details>
  );
}
'''

FILES[FRONT / "components/SearchPanel.js"] = r'''"use client";

import { Fragment, useEffect, useId, useMemo, useRef, useState, useTransition } from 'react';
import { useRouter } from 'next/navigation';
import { fetchSuggestions } from '../lib/api';
import { buildHref } from '../lib/params';
import { TRENDING } from '../lib/trending';
import { useT } from './I18nProvider';

const RECENT_KEY = 'jobscope:recent';
const EMPTY = { titles: [], companies: [], locations: [] };

function loadRecent() {
  try {
    return JSON.parse(localStorage.getItem(RECENT_KEY) || '[]').slice(0, 5);
  } catch {
    return [];
  }
}

function saveRecent(term) {
  try {
    const next = [term, ...loadRecent().filter((t) => t.toLowerCase() !== term.toLowerCase())].slice(0, 5);
    localStorage.setItem(RECENT_KEY, JSON.stringify(next));
  } catch {}
}

function removeRecent(term) {
  try {
    const next = loadRecent().filter((t) => t !== term);
    localStorage.setItem(RECENT_KEY, JSON.stringify(next));
  } catch {}
}

function clearRecent() {
  try {
    localStorage.removeItem(RECENT_KEY);
  } catch {}
}

function Highlight({ text, term }) {
  const words = term.trim().split(/\s+/).filter(Boolean).map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  if (!words.length) return text;
  const parts = text.split(new RegExp(`(${words.join('|')})`, 'ig'));
  return parts.map((part, i) => (i % 2 ? <mark key={i}>{part}</mark> : part));
}

function Icon({ name }) {
  const shapes = {
    search: <><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></>,
    building: <><path d="M4 21V5a1 1 0 0 1 1-1h8a1 1 0 0 1 1 1v16" /><path d="M14 9h5a1 1 0 0 1 1 1v11" /><path d="M8 8h2M8 12h2M8 16h2" /></>,
    pin: <><path d="M12 21s7-6.2 7-11a7 7 0 1 0-14 0c0 4.8 7 11 7 11Z" /><circle cx="12" cy="10" r="2.5" /></>,
    clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
    trend: <path d="m3 17 6-6 4 4 8-8M15 7h6v6" />,
  };
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {shapes[name]}
    </svg>
  );
}

export default function SearchPanel({ params }) {
  const t = useT();
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const listId = useId();
  const formRef = useRef(null);
  const inputRef = useRef(null);

  const [value, setValue] = useState(params.q);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const [data, setData] = useState(EMPTY);
  const [recent, setRecent] = useState([]);

  // Keep the box in sync with the URL (back/forward, removing a chip).
  useEffect(() => { setValue(params.q); }, [params.q]);
  useEffect(() => { setRecent(loadRecent()); }, []);

  // Close when clicking outside.
  useEffect(() => {
    const onDown = (e) => {
      if (formRef.current && !formRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('pointerdown', onDown);
    return () => document.removeEventListener('pointerdown', onDown);
  }, []);

  // Debounced suggestions.
  const term = value.trim();
  useEffect(() => {
    if (term.length < 2) {
      setData(EMPTY);
      return;
    }
    const ctrl = new AbortController();
    const timer = setTimeout(async () => {
      try {
        setData(await fetchSuggestions(term, ctrl.signal));
        setActive(-1);
      } catch {}
    }, 160);
    return () => {
      clearTimeout(timer);
      ctrl.abort();
    };
  }, [term]);

  const items = useMemo(() => {
    if (term.length >= 2) {
      return [
        ...data.titles.map((label) => ({ type: 'query', icon: 'search', label, group: 'groupJobs' })),
        ...data.companies.map((label) => ({ type: 'company', icon: 'building', label, group: 'groupCompanies' })),
        ...data.locations.map((label) => ({ type: 'location', icon: 'pin', label, group: 'groupLocations' })),
      ];
    }
    return [
      ...recent.map((label) => ({ type: 'query', icon: 'clock', label, group: 'groupRecent', removable: true })),
      ...TRENDING.slice(0, 6).map((label) => ({ type: 'query', icon: 'trend', label, group: 'groupTrending' })),
    ];
  }, [term, data, recent]);

  const expanded = open && items.length > 0;

  function navigate(overrides) {
    setOpen(false);
    setActive(-1);
    startTransition(() => router.push(buildHref(params, overrides)));
  }

  function choose(item) {
    if (item.type === 'company') {
      setValue('');
      navigate({ q: '', company: item.label });
    } else if (item.type === 'location') {
      setValue('');
      navigate({ q: '', location: item.label });
    } else {
      setValue(item.label);
      saveRecent(item.label);
      setRecent(loadRecent());
      navigate({ q: item.label });
    }
  }

  function onSubmit(e) {
    e.preventDefault();
    if (active >= 0 && items[active]) {
      choose(items[active]);
      return;
    }
    const q = value.trim();
    if (q) {
      saveRecent(q);
      setRecent(loadRecent());
    }
    navigate({ q });
  }

  function onKeyDown(e) {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (!open) setOpen(true);
      setActive((a) => (items.length ? (a + 1) % items.length : -1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActive((a) => (items.length ? (a <= 0 ? items.length - 1 : a - 1) : -1));
    } else if (e.key === 'Delete' && active >= 0 && items[active]?.removable) {
      e.preventDefault();
      forget(items[active].label);
    } else if (e.key === 'Escape') {
      setOpen(false);
      setActive(-1);
    } else if (e.key === 'Tab') {
      setOpen(false);
    }
  }

  function forget(label) {
    removeRecent(label);
    setRecent(loadRecent());
    setActive(-1);
  }

  const hasRecent = term.length < 2 && recent.length > 0;

  return (
    <form ref={formRef} role="search" className="searchbar" onSubmit={onSubmit} aria-busy={isPending}>
      <div className="field">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
          <circle cx="11" cy="11" r="7" />
          <path d="m20 20-3.5-3.5" />
        </svg>
        <input
          ref={inputRef}
          type="text"
          role="combobox"
          aria-label={t('search.aria')}
          aria-autocomplete="list"
          aria-expanded={expanded}
          aria-controls={`${listId}-list`}
          aria-activedescendant={active >= 0 ? `${listId}-opt-${active}` : undefined}
          placeholder={t('search.placeholder')}
          autoComplete="off"
          spellCheck={false}
          enterKeyHint="search"
          maxLength={100}
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            setOpen(true);
            setActive(-1);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
        />
        {value && (
          <button
            type="button"
            className="clear"
            aria-label={t('search.clear')}
            onClick={() => {
              setValue('');
              setOpen(true);
              inputRef.current?.focus();
            }}
          >
            ×
          </button>
        )}
      </div>

      <button type="submit" className="go" disabled={isPending}>
        {isPending ? <><span className="spinner" aria-hidden="true" /><span className="sr">{t('search.busy')}</span></> : t('search.go')}
      </button>

      {expanded && (
        <div className="suggest">
          <ul id={`${listId}-list`} role="listbox" aria-label={t('search.suggestions')}>
            {items.map((it, i) => (
              <Fragment key={`${it.group}-${it.label}`}>
                {(i === 0 || items[i - 1].group !== it.group) && (
                  <li role="presentation" className="sg-group">{t(`search.${it.group}`)}</li>
                )}
                <li
                  id={`${listId}-opt-${i}`}
                  role="option"
                  aria-selected={i === active}
                  className="sg-item"
                  onPointerDown={(e) => {
                    e.preventDefault();
                    choose(it);
                  }}
                  onMouseEnter={() => setActive(i)}
                >
                  <Icon name={it.icon} />
                  <span className="sg-label"><Highlight text={it.label} term={term.length >= 2 ? term : ''} /></span>
                  {it.removable && (
                    <button
                      type="button"
                      className="sg-remove"
                      tabIndex={-1}
                      title={t('search.removeTitle')}
                      aria-label={t('search.removeRecent', { label: it.label })}
                      onPointerDown={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        forget(it.label);
                      }}
                    >
                      ×
                    </button>
                  )}
                </li>
              </Fragment>
            ))}
          </ul>
          {hasRecent && (
            <div className="sg-foot">
              <button
                type="button"
                onPointerDown={(e) => {
                  e.preventDefault();
                  clearRecent();
                  setRecent([]);
                }}
              >
                {t('search.clearRecent')}
              </button>
            </div>
          )}
        </div>
      )}
    </form>
  );
}
'''

# =====================================================================
# FRONTEND: auth
# =====================================================================

FILES[FRONT / "components/auth/PasswordField.js"] = r'''"use client";

import { useState } from 'react';
import { useT } from '../I18nProvider';

export default function PasswordField({ id, name, label, autoComplete, error, hint, minLength }) {
  const t = useT();
  const [shown, setShown] = useState(false);
  const describedBy = error ? `${id}-err` : hint ? `${id}-hint` : undefined;

  return (
    <div className="fld">
      <label htmlFor={id}>{label}</label>
      <div className="pw">
        <input
          id={id}
          name={name}
          type={shown ? 'text' : 'password'}
          autoComplete={autoComplete}
          required
          minLength={minLength}
          aria-invalid={error ? 'true' : undefined}
          aria-describedby={describedBy}
        />
        <button type="button" onClick={() => setShown(!shown)} aria-pressed={shown}>
          {shown ? t('auth.hide') : t('auth.show')}
          <span className="sr">{t('auth.passwordSr')}</span>
        </button>
      </div>
      {error ? (
        <p className="err" id={`${id}-err`}>{error}</p>
      ) : hint ? (
        <p className="hint" id={`${id}-hint`}>{hint}</p>
      ) : null}
    </div>
  );
}
'''

FILES[FRONT / "components/auth/LoginForm.js"] = r'''"use client";

import { useActionState } from 'react';
import { loginAction } from '../../app/auth/actions';
import { useT } from '../I18nProvider';
import Field from './Field';
import PasswordField from './PasswordField';
import SubmitButton from './SubmitButton';

const INITIAL = { errors: {}, error: '', success: '', values: {} };

export default function LoginForm({ next = '/' }) {
  const t = useT();
  const [state, action] = useActionState(loginAction, INITIAL);

  return (
    <form action={action} className="auth-form">
      {state.error && <p className="alert" role="alert">{state.error}</p>}
      <input type="hidden" name="next" value={next} />

      <Field
        id="email"
        name="email"
        type="email"
        label={t('auth.email')}
        autoComplete="email"
        defaultValue={state.values.email}
        error={state.errors.email}
        maxLength={255}
        autoFocus
      />
      <PasswordField
        id="password"
        name="password"
        label={t('auth.password')}
        autoComplete="current-password"
        error={state.errors.password}
      />

      <SubmitButton pendingLabel={t('login.pending')}>{t('login.submit')}</SubmitButton>
    </form>
  );
}
'''

FILES[FRONT / "components/auth/RegisterForm.js"] = r'''"use client";

import { useActionState } from 'react';
import { registerAction } from '../../app/auth/actions';
import { useT } from '../I18nProvider';
import Field from './Field';
import PasswordField from './PasswordField';
import SubmitButton from './SubmitButton';

const INITIAL = { errors: {}, error: '', success: '', values: {} };

export default function RegisterForm() {
  const t = useT();
  const [state, action] = useActionState(registerAction, INITIAL);

  return (
    <form action={action} className="auth-form">
      {state.error && <p className="alert" role="alert">{state.error}</p>}

      <Field
        id="name"
        name="name"
        label={t('register.name')}
        autoComplete="name"
        defaultValue={state.values.name}
        error={state.errors.name}
        maxLength={100}
        autoFocus
      />
      <Field
        id="email"
        name="email"
        type="email"
        label={t('auth.email')}
        autoComplete="email"
        defaultValue={state.values.email}
        error={state.errors.email}
        maxLength={255}
      />
      <PasswordField
        id="password"
        name="password"
        label={t('auth.password')}
        autoComplete="new-password"
        minLength={8}
        hint={t('auth.pwHint')}
        error={state.errors.password}
      />
      <PasswordField
        id="password_confirmation"
        name="password_confirmation"
        label={t('register.confirm')}
        autoComplete="new-password"
        minLength={8}
        error={state.errors.password_confirmation}
      />

      <SubmitButton pendingLabel={t('register.pending')}>{t('register.submit')}</SubmitButton>
    </form>
  );
}
'''

FILES[FRONT / "components/auth/PasswordForm.js"] = r'''"use client";

import { useActionState } from 'react';
import { updatePasswordAction } from '../../app/auth/actions';
import { useT } from '../I18nProvider';
import PasswordField from './PasswordField';
import SubmitButton from './SubmitButton';

const INITIAL = { errors: {}, error: '', success: '', values: {} };

export default function PasswordForm() {
  const t = useT();
  const [state, action] = useActionState(updatePasswordAction, INITIAL);

  return (
    <form action={action} className="auth-form">
      {state.error && <p className="alert" role="alert">{state.error}</p>}
      {state.success && <p className="alert ok" role="status">{state.success}</p>}

      <PasswordField
        id="current_password"
        name="current_password"
        label={t('pw.current')}
        autoComplete="current-password"
        error={state.errors.current_password}
      />
      <PasswordField
        id="password"
        name="password"
        label={t('pw.new')}
        autoComplete="new-password"
        minLength={8}
        hint={t('auth.pwHint')}
        error={state.errors.password}
      />
      <PasswordField
        id="password_confirmation"
        name="password_confirmation"
        label={t('pw.confirm')}
        autoComplete="new-password"
        minLength={8}
        error={state.errors.password_confirmation}
      />

      <SubmitButton pendingLabel={t('pw.pending')}>{t('pw.submit')}</SubmitButton>
    </form>
  );
}
'''

FILES[FRONT / "app/auth/actions.js"] = r'''"use server";

import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { api, getToken, setSession, SESSION_COOKIE } from '../../lib/auth';
import { getT } from '../../lib/i18n/server';

const text = (form, key) => String(form.get(key) ?? '').trim();
const raw = (form, key) => String(form.get(key) ?? '');

function safeNext(value) {
  const v = String(value ?? '');
  return v.startsWith('/') && !v.startsWith('//') && !v.includes('\\') ? v : '/';
}

function fail(t, res, values) {
  if (res.status === 0) {
    return { errors: {}, error: t('err.network'), success: '', values };
  }

  // Field messages come from Laravel already translated (X-Locale header).
  const errors = {};
  for (const [field, messages] of Object.entries(res.data?.errors ?? {})) {
    errors[field] = Array.isArray(messages) ? messages[0] : String(messages);
  }

  let error = '';
  if (!Object.keys(errors).length) {
    error = res.status === 429 ? t('err.tooMany') : t('err.generic');
  }
  return { errors, error, success: '', values };
}

export async function registerAction(_prev, formData) {
  const t = await getT();
  const values = { name: text(formData, 'name'), email: text(formData, 'email') };

  const res = await api('/auth/register', {
    method: 'POST',
    body: {
      ...values,
      password: raw(formData, 'password'),
      password_confirmation: raw(formData, 'password_confirmation'),
    },
  });

  if (!res.ok) return fail(t, res, values);

  await setSession(res.data.token);
  redirect('/');
}

export async function loginAction(_prev, formData) {
  const t = await getT();
  const values = { email: text(formData, 'email') };
  const next = safeNext(formData.get('next'));

  const res = await api('/auth/login', {
    method: 'POST',
    body: { ...values, password: raw(formData, 'password') },
  });

  if (!res.ok) return fail(t, res, values);

  await setSession(res.data.token);
  redirect(next);
}

export async function logoutAction() {
  const token = await getToken();
  if (token) await api('/auth/logout', { method: 'POST', token });

  const jar = await cookies();
  jar.delete(SESSION_COOKIE);
  redirect('/');
}

export async function updatePasswordAction(_prev, formData) {
  const t = await getT();
  const token = await getToken();
  if (!token) redirect('/login?next=%2Faccount%2Fpassword');

  const res = await api('/auth/password', {
    method: 'PUT',
    token,
    body: {
      current_password: raw(formData, 'current_password'),
      password: raw(formData, 'password'),
      password_confirmation: raw(formData, 'password_confirmation'),
    },
  });

  if (res.status === 401) redirect('/login?next=%2Faccount%2Fpassword');
  if (!res.ok) return fail(t, res, {});

  return { errors: {}, error: '', success: t('pw.updated'), values: {} };
}
'''

FILES[FRONT / "app/login/page.js"] = r'''import Link from 'next/link';
import { redirect } from 'next/navigation';
import { getUser } from '../../lib/auth';
import { getT } from '../../lib/i18n/server';
import AuthShell from '../../components/auth/AuthShell';
import LoginForm from '../../components/auth/LoginForm';

export async function generateMetadata() {
  const t = await getT();
  return {
    title: t('meta.login.title'),
    description: t('meta.login.desc'),
    robots: { index: false, follow: false },
    alternates: { canonical: '/login' },
  };
}

export default async function LoginPage({ searchParams }) {
  if (await getUser()) redirect('/');

  const t = await getT();
  const sp = await searchParams;
  const next = typeof sp?.next === 'string' ? sp.next : '/';

  return (
    <AuthShell
      title={t('login.title')}
      lead={t('login.lead')}
      footer={<>{t('login.footer')} <Link href="/register" prefetch={false}>{t('login.footerLink')}</Link></>}
    >
      <LoginForm next={next} />
    </AuthShell>
  );
}
'''

FILES[FRONT / "app/register/page.js"] = r'''import Link from 'next/link';
import { redirect } from 'next/navigation';
import { getUser } from '../../lib/auth';
import { getT } from '../../lib/i18n/server';
import AuthShell from '../../components/auth/AuthShell';
import RegisterForm from '../../components/auth/RegisterForm';

export async function generateMetadata() {
  const t = await getT();
  return {
    title: t('meta.register.title'),
    description: t('meta.register.desc'),
    robots: { index: false, follow: false },
    alternates: { canonical: '/register' },
  };
}

export default async function RegisterPage() {
  if (await getUser()) redirect('/');

  const t = await getT();

  return (
    <AuthShell
      title={t('register.title')}
      lead={t('register.lead')}
      footer={<>{t('register.footer')} <Link href="/login" prefetch={false}>{t('register.footerLink')}</Link></>}
    >
      <RegisterForm />
    </AuthShell>
  );
}
'''

FILES[FRONT / "app/account/password/page.js"] = r'''import { redirect } from 'next/navigation';
import { getUser } from '../../../lib/auth';
import { getT } from '../../../lib/i18n/server';
import AuthShell from '../../../components/auth/AuthShell';
import PasswordForm from '../../../components/auth/PasswordForm';

export async function generateMetadata() {
  const t = await getT();
  return {
    title: t('meta.password.title'),
    description: t('meta.password.desc'),
    robots: { index: false, follow: false },
    alternates: { canonical: '/account/password' },
  };
}

export default async function PasswordPage() {
  const user = await getUser();
  if (!user) redirect('/login?next=%2Faccount%2Fpassword');

  const t = await getT();

  return (
    <AuthShell title={t('pw.title')} lead={t('pw.lead', { email: user.email })}>
      <PasswordForm />
    </AuthShell>
  );
}
'''

# =====================================================================
# FRONTEND: chatbot (language = website language)
# =====================================================================

FILES[FRONT / "app/chat-api/key/route.js"] = r'''import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { COOKIE_NAME, sameOrigin, seal } from '../../../lib/keyvault';
import { getT } from '../../../lib/i18n/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const WEEK = 60 * 60 * 24 * 7;
const EMBED_MODEL = process.env.OPENAI_EMBED_MODEL || 'text-embedding-3-small';

export async function POST(request) {
  const t = await getT();

  if (!sameOrigin(request)) {
    return NextResponse.json({ error: t('key.forbidden') }, { status: 403 });
  }

  let body = null;
  try {
    body = await request.json();
  } catch {}

  const key = String(body?.key ?? '').trim();
  if (!/^sk-[\w-]{16,}$/.test(key) || key.length > 250) {
    return NextResponse.json({ error: t('key.format') }, { status: 400 });
  }

  // Verify the key with a tiny embeddings request: it checks the key AND the exact permission we use.
  let check;
  try {
    check = await fetch('https://api.openai.com/v1/embeddings', {
      method: 'POST',
      headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: EMBED_MODEL, input: 'ok' }),
      cache: 'no-store',
      signal: AbortSignal.timeout(20000),
    });
  } catch {
    return NextResponse.json({ error: t('key.reach') }, { status: 502 });
  }

  if (check.status === 401) {
    return NextResponse.json({ error: t('key.rejected') }, { status: 400 });
  }

  if (!check.ok) {
    const info = await check.json().catch(() => null);
    if (check.status === 429 && info?.error?.code === 'insufficient_quota') {
      return NextResponse.json({ error: t('key.quota') }, { status: 400 });
    }
    if (check.status === 429) {
      return NextResponse.json({ error: t('key.rate') }, { status: 429 });
    }
    if (check.status === 403 || check.status === 404) {
      const detail = String(info?.error?.message ?? '').slice(0, 160);
      return NextResponse.json(
        { error: t('key.model') + (detail ? t('key.modelDetail', { detail }) : '') },
        { status: 400 }
      );
    }
    return NextResponse.json({ error: t('key.verify') }, { status: 502 });
  }

  let sealed;
  try {
    sealed = seal(key);
  } catch {
    return NextResponse.json({ error: t('key.secret') }, { status: 500 });
  }

  const jar = await cookies();
  jar.set(COOKIE_NAME, sealed, {
    httpOnly: true,
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
    path: '/chat-api',
    maxAge: WEEK,
  });

  return NextResponse.json({ connected: true });
}

export async function DELETE(request) {
  const t = await getT();

  if (!sameOrigin(request)) {
    return NextResponse.json({ error: t('key.forbidden') }, { status: 403 });
  }
  const jar = await cookies();
  jar.delete({ name: COOKIE_NAME, path: '/chat-api' });
  return NextResponse.json({ connected: false });
}
'''

FILES[FRONT / "app/chat-api/message/route.js"] = r'''import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { COOKIE_NAME, sameOrigin, unseal } from '../../../lib/keyvault';
import { getLocale, getT } from '../../../lib/i18n/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const API = process.env.API_INTERNAL_URL || 'http://127.0.0.1:8000/api';

export async function POST(request) {
  const t = await getT();
  const locale = await getLocale();

  if (!sameOrigin(request)) {
    return NextResponse.json({ error: t('key.forbidden') }, { status: 403 });
  }

  const jar = await cookies();
  const raw = jar.get(COOKIE_NAME)?.value;
  const key = raw ? unseal(raw) : null;

  if (!key) {
    return NextResponse.json({ code: 'key_required', reply: t('msg.needKey') }, { status: 401 });
  }

  let body = null;
  try {
    body = await request.json();
  } catch {}

  const message = String(body?.message ?? '').trim().slice(0, 500);
  if (!message) {
    return NextResponse.json({ reply: t('msg.empty') }, { status: 400 });
  }

  const history = Array.isArray(body?.history)
    ? body.history
        .slice(-12)
        .map((h) => ({ role: h?.role === 'user' ? 'user' : 'bot', text: String(h?.text ?? '').slice(0, 1000) }))
        .filter((h) => h.text)
    : [];
  const lastSearch = body?.last_search && typeof body.last_search === 'object' ? body.last_search : null;

  try {
    const res = await fetch(`${API}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        'X-OpenAI-Key': key,
        // The chatbot answers in the website language, not the language the user types in.
        'X-Locale': locale,
      },
      body: JSON.stringify({ message, history, last_search: lastSearch }),
      cache: 'no-store',
      signal: AbortSignal.timeout(90000),
    });
    const data = await res.json().catch(() => ({ reply: t('chat.errGeneric') }));
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ code: 'unreachable', reply: t('msg.unreachable') }, { status: 502 });
  }
}
'''

FILES[FRONT / "components/chat/ChatWidget.js"] = r'''"use client";

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useT } from '../I18nProvider';

const STORAGE_KEY = 'hirelume:chat:v4';

function safeUrl(url) {
  try {
    const u = new URL(url);
    return u.protocol === 'http:' || u.protocol === 'https:' ? u.href : null;
  } catch {
    return null;
  }
}

function ChatIcon() {
  return (
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12Z" />
      <path d="M9 11h6M9 14h3" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true">
      <path d="M6 6l12 12M18 6 6 18" />
    </svg>
  );
}

export default function ChatWidget() {
  const t = useT();
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState('checking'); // checking | needs_key | ready
  const [messages, setMessages] = useState([]); // the welcome bubble is rendered from t(), never stored
  const [lastSearch, setLastSearch] = useState(null);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [keyInput, setKeyInput] = useState('');
  const [keyBusy, setKeyBusy] = useState(false);
  const [keyError, setKeyError] = useState('');
  const endRef = useRef(null);
  const inputRef = useRef(null);

  const suggestions = [t('chat.s1'), t('chat.s2'), t('chat.s3'), t('chat.s4')];

  // Restore the conversation for this browser tab (the API key is never stored here).
  useEffect(() => {
    try {
      const saved = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || 'null');
      if (saved && Array.isArray(saved.messages)) {
        setMessages(saved.messages.slice(-30));
        setLastSearch(saved.lastSearch || null);
      }
    } catch {}
  }, []);

  useEffect(() => {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ messages: messages.slice(-30), lastSearch }));
    } catch {}
  }, [messages, lastSearch]);

  // Ask the server whether a key is already connected (first time the panel opens).
  useEffect(() => {
    if (!open || status !== 'checking') return;
    let cancelled = false;
    fetch('/chat-api/status', { cache: 'no-store' })
      .then((r) => r.json())
      .then((d) => {
        if (!cancelled) setStatus(d.connected ? 'ready' : 'needs_key');
      })
      .catch(() => {
        if (!cancelled) setStatus('needs_key');
      });
    return () => {
      cancelled = true;
    };
  }, [open, status]);

  useEffect(() => {
    if (!open) return;
    endRef.current?.scrollIntoView({ block: 'end' });
    if (status === 'ready') inputRef.current?.focus();
  }, [open, status, messages, busy]);

  async function connect(e) {
    e.preventDefault();
    if (keyBusy) return;
    setKeyBusy(true);
    setKeyError('');
    try {
      const res = await fetch('/chat-api/key', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: keyInput.trim() }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setKeyError(data.error || t('chat.connectFail'));
        return;
      }
      setKeyInput('');
      setStatus('ready');
    } catch {
      setKeyError(t('chat.connectNet'));
    } finally {
      setKeyBusy(false);
    }
  }

  async function disconnect() {
    try {
      await fetch('/chat-api/key', { method: 'DELETE' });
    } catch {}
    setStatus('needs_key');
    setKeyError('');
  }

  async function send(raw) {
    const text = raw.trim();
    if (!text || busy) return;

    const history = messages.slice(-8).map((m) => ({ role: m.role, text: m.text }));
    setMessages((m) => [...m, { role: 'user', text }]);
    setInput('');
    setBusy(true);

    try {
      const res = await fetch('/chat-api/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, history, last_search: lastSearch }),
      });
      const data = await res.json().catch(() => null);

      if (res.status === 401 && (data?.code === 'key_required' || data?.code === 'invalid_key')) {
        setMessages((m) => m.slice(0, -1));
        setInput(text);
        setKeyError(data.reply || t('chat.needKey'));
        setStatus('needs_key');
        return;
      }

      if (!res.ok || !data?.reply) {
        setMessages((m) => [...m, { role: 'bot', text: data?.reply || t('chat.errGeneric'), jobs: [] }]);
        return;
      }

      setLastSearch(data.last_search || null);
      setMessages((m) => [
        ...m,
        {
          role: 'bot',
          text: data.reply,
          jobs: data.jobs || [],
          total: data.total || 0,
          searchUrl: data.search_url,
          followUps: data.follow_ups || [],
          mode: data.mode,
        },
      ]);
    } catch {
      setMessages((m) => [...m, { role: 'bot', text: t('chat.errReach'), jobs: [] }]);
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setMessages([]);
    setLastSearch(null);
    try {
      sessionStorage.removeItem(STORAGE_KEY);
    } catch {}
  }

  const lastMessage = messages[messages.length - 1];

  return (
    <>
      {open && (
        <section
          id="chat-panel"
          className="cb-panel"
          role="dialog"
          aria-label={t('chat.dialog')}
          onKeyDown={(e) => {
            if (e.key === 'Escape') setOpen(false);
          }}
        >
          <header className="cb-head">
            <span className="cb-avatar" aria-hidden="true"><ChatIcon /></span>
            <div className="cb-title">
              <strong>{t('chat.title')}</strong>
              <span>{t('chat.powered')}</span>
            </div>
            {status === 'ready' && (
              <>
                <button type="button" className="cb-icon" onClick={reset} title={t('chat.newTitle')}>{t('chat.new')}</button>
                <button type="button" className="cb-icon" onClick={disconnect} title={t('chat.disconnectTitle')}>
                  {t('chat.disconnect')}
                </button>
              </>
            )}
            <button type="button" className="cb-icon" onClick={() => setOpen(false)} aria-label={t('chat.closeBtn')}>
              <CloseIcon />
            </button>
          </header>

          {status === 'checking' && (
            <div className="cb-body"><p className="cb-note">{t('chat.loading')}</p></div>
          )}

          {status === 'needs_key' && (
            <div className="cb-body">
              <form className="cb-connect" onSubmit={connect}>
                <h3>{t('chat.connectTitle')}</h3>
                <p>{t('chat.connectText')}</p>
                {keyError && <p className="cb-error" role="alert">{keyError}</p>}
                <label htmlFor="openai-key" className="sr">{t('chat.keyLabel')}</label>
                <input
                  id="openai-key"
                  type="password"
                  dir="ltr"
                  autoComplete="off"
                  spellCheck={false}
                  placeholder={t('chat.keyPlaceholder')}
                  value={keyInput}
                  onChange={(e) => setKeyInput(e.target.value)}
                />
                <button type="submit" disabled={keyBusy || keyInput.trim().length < 20}>
                  {keyBusy ? t('chat.connecting') : t('chat.connect')}
                </button>
                <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer">
                  {t('chat.getKey')}
                </a>
              </form>
            </div>
          )}

          {status === 'ready' && (
            <>
              <div className="cb-body" role="log" aria-live="polite" aria-relevant="additions">
                <div className="cb-row">
                  <div className="cb-bubble"><p>{t('chat.welcome')}</p></div>
                </div>

                {messages.map((m, i) => (
                  <div key={i} className={m.role === 'user' ? 'cb-row user' : 'cb-row'}>
                    <div className={m.role === 'user' ? 'cb-bubble user' : 'cb-bubble'}>
                      {m.text.split('\n').map((line, k) => (
                        <p key={k}>{line}</p>
                      ))}

                      {m.jobs?.length > 0 && (
                        <ul className="cb-jobs">
                          {m.jobs.map((j) => {
                            const href = safeUrl(j.url);
                            const inner = (
                              <>
                                <span className="cb-job-title">{j.title}</span>
                                <span className="cb-job-meta">
                                  {j.company}
                                  {j.location ? ` · ${j.location}` : ''}
                                </span>
                                <span className="cb-job-foot">
                                  <span className="cb-job-tag">{j.source_label}</span>
                                  {j.match != null && <span className="cb-match">{t('chat.match', { n: j.match })}</span>}
                                </span>
                              </>
                            );
                            return (
                              <li key={j.id}>
                                {href ? (
                                  <a className="cb-job" href={href} target="_blank" rel="nofollow noopener noreferrer">{inner}</a>
                                ) : (
                                  <span className="cb-job">{inner}</span>
                                )}
                              </li>
                            );
                          })}
                        </ul>
                      )}

                      {m.mode === 'keyword' && m.jobs?.length > 0 && (
                        <p className="cb-note">{t('chat.keyword')}</p>
                      )}

                      {m.searchUrl && m.jobs?.length > 0 && (
                        <Link className="cb-more" href={m.searchUrl} prefetch={false} onClick={() => setOpen(false)}>
                          {t('chat.openSearch')}
                        </Link>
                      )}
                    </div>
                  </div>
                ))}

                {busy && (
                  <div className="cb-row">
                    <div className="cb-bubble cb-typing" aria-label={t('chat.typing')}>
                      <span /><span /><span />
                    </div>
                  </div>
                )}

                {!busy && messages.length === 0 && (
                  <ul className="cb-suggest" aria-label={t('chat.suggestions')}>
                    {suggestions.map((s) => (
                      <li key={s}><button type="button" onClick={() => send(s)}>{s}</button></li>
                    ))}
                  </ul>
                )}

                {!busy && lastMessage?.followUps?.length > 0 && (
                  <ul className="cb-suggest" aria-label={t('chat.followups')}>
                    {lastMessage.followUps.map((s) => (
                      <li key={s}><button type="button" onClick={() => send(s)}>{s}</button></li>
                    ))}
                  </ul>
                )}
                <div ref={endRef} />
              </div>

              <form
                className="cb-form"
                onSubmit={(e) => {
                  e.preventDefault();
                  send(input);
                }}
              >
                <input
                  ref={inputRef}
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder={t('chat.input')}
                  aria-label={t('chat.inputLabel')}
                  maxLength={500}
                  autoComplete="off"
                  enterKeyHint="send"
                />
                <button type="submit" disabled={busy || !input.trim()} aria-label={t('chat.send')}>
                  <svg className="cb-send" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M5 12h14M13 6l6 6-6 6" />
                  </svg>
                </button>
              </form>
            </>
          )}
        </section>
      )}

      <button
        type="button"
        className="cb-launch"
        onClick={() => setOpen(!open)}
        aria-label={open ? t('chat.close') : t('chat.open')}
        aria-expanded={open}
        aria-controls="chat-panel"
      >
        {open ? <CloseIcon /> : <ChatIcon />}
      </button>
    </>
  );
}
'''

# =====================================================================
# FRONTEND: one consolidated stylesheet (light + dark + RTL)
# =====================================================================

FILES[FRONT / "app/globals.css"] = r'''/* ===== Hirelume: themes (dark default, light), RTL-ready ===== */
:root {
  color-scheme: dark;
  --bg: #080c1a;
  --glow-1: rgba(129, 140, 248, .28);
  --glow-2: rgba(94, 234, 212, .16);
  --glow-3: rgba(244, 114, 182, .12);
  --panel: rgba(255, 255, 255, .045);
  --panel-hover: rgba(255, 255, 255, .065);
  --panel-strong: rgba(255, 255, 255, .08);
  --line: rgba(255, 255, 255, .1);
  --text: #eef1fb;
  --text-soft: #cdd5f0;
  --muted: #a3accb;
  --placeholder: #8791b5;
  --surface: #0e1328;
  --surface-2: #0b1020;
  --glass: rgba(14, 19, 40, .82);
  --header-bg: rgba(8, 12, 26, .72);
  --accent: #5eead4;
  --accent2: #818cf8;
  --hot: #f472b6;
  --accent-text: #5eead4;
  --grad-a: #5eead4;
  --grad-b: #818cf8;
  --grad-c: #f472b6;
  --on-accent: #06101f;
  --hover-line: rgba(94, 234, 212, .5);
  --focus-ring: rgba(94, 234, 212, .14);
  --select-bg: rgba(129, 140, 248, .2);
  --badge-bg: rgba(129, 140, 248, .2);
  --badge-fg: #c7d2fe;
  --new-bg: rgba(244, 114, 182, .18);
  --new-fg: #fbcfe8;
  --remote-bg: rgba(94, 234, 212, .16);
  --remote-fg: #99f6e4;
  --chip-bg: rgba(94, 234, 212, .12);
  --chip-line: rgba(94, 234, 212, .35);
  --danger-bg: rgba(248, 113, 113, .12);
  --danger-line: rgba(248, 113, 113, .4);
  --danger-fg: #fecaca;
  --danger-text: #fca5a5;
  --ok-bg: rgba(94, 234, 212, .12);
  --ok-line: rgba(94, 234, 212, .4);
  --ok-fg: #99f6e4;
  --shadow-pop: 0 30px 80px -20px rgba(0, 0, 0, .7);
  --shadow-glow: 0 20px 60px -20px rgba(129, 140, 248, .45);
  --radius: 18px;
  --sun: inline-block;
  --moon: none;
}

:root[data-theme="light"] {
  color-scheme: light;
  --bg: #f4f6ff;
  --glow-1: rgba(129, 140, 248, .22);
  --glow-2: rgba(94, 234, 212, .22);
  --glow-3: rgba(244, 114, 182, .10);
  --panel: rgba(255, 255, 255, .72);
  --panel-hover: #ffffff;
  --panel-strong: rgba(15, 21, 48, .06);
  --line: rgba(15, 21, 48, .12);
  --text: #0f1530;
  --text-soft: #2c3558;
  --muted: #566083;
  --placeholder: #7a84a6;
  --surface: #ffffff;
  --surface-2: #ffffff;
  --glass: rgba(255, 255, 255, .9);
  --header-bg: rgba(244, 246, 255, .85);
  --accent-text: #0f766e;
  --grad-a: #0d9488;
  --grad-b: #4f46e5;
  --grad-c: #db2777;
  --hover-line: rgba(13, 148, 136, .55);
  --focus-ring: rgba(13, 148, 136, .18);
  --select-bg: rgba(99, 102, 241, .12);
  --badge-bg: rgba(99, 102, 241, .12);
  --badge-fg: #4338ca;
  --new-bg: rgba(236, 72, 153, .12);
  --new-fg: #be185d;
  --remote-bg: rgba(13, 148, 136, .12);
  --remote-fg: #0f766e;
  --chip-bg: rgba(13, 148, 136, .1);
  --chip-line: rgba(13, 148, 136, .35);
  --danger-bg: rgba(220, 38, 38, .08);
  --danger-line: rgba(220, 38, 38, .35);
  --danger-fg: #991b1b;
  --danger-text: #b91c1c;
  --ok-bg: rgba(13, 148, 136, .1);
  --ok-line: rgba(13, 148, 136, .35);
  --ok-fg: #0f766e;
  --shadow-pop: 0 24px 60px -20px rgba(30, 41, 90, .35);
  --shadow-glow: 0 20px 60px -24px rgba(79, 70, 229, .35);
  --sun: none;
  --moon: inline-block;
}

/* Until a choice is saved, follow the system setting. */
@media (prefers-color-scheme: light) {
  :root:not([data-theme]) {
    color-scheme: light;
    --bg: #f4f6ff;
    --glow-1: rgba(129, 140, 248, .22);
    --glow-2: rgba(94, 234, 212, .22);
    --glow-3: rgba(244, 114, 182, .10);
    --panel: rgba(255, 255, 255, .72);
    --panel-hover: #ffffff;
    --panel-strong: rgba(15, 21, 48, .06);
    --line: rgba(15, 21, 48, .12);
    --text: #0f1530;
    --text-soft: #2c3558;
    --muted: #566083;
    --placeholder: #7a84a6;
    --surface: #ffffff;
    --surface-2: #ffffff;
    --glass: rgba(255, 255, 255, .9);
    --header-bg: rgba(244, 246, 255, .85);
    --accent-text: #0f766e;
    --grad-a: #0d9488;
    --grad-b: #4f46e5;
    --grad-c: #db2777;
    --hover-line: rgba(13, 148, 136, .55);
    --focus-ring: rgba(13, 148, 136, .18);
    --select-bg: rgba(99, 102, 241, .12);
    --badge-bg: rgba(99, 102, 241, .12);
    --badge-fg: #4338ca;
    --new-bg: rgba(236, 72, 153, .12);
    --new-fg: #be185d;
    --remote-bg: rgba(13, 148, 136, .12);
    --remote-fg: #0f766e;
    --chip-bg: rgba(13, 148, 136, .1);
    --chip-line: rgba(13, 148, 136, .35);
    --danger-bg: rgba(220, 38, 38, .08);
    --danger-line: rgba(220, 38, 38, .35);
    --danger-fg: #991b1b;
    --danger-text: #b91c1c;
    --ok-bg: rgba(13, 148, 136, .1);
    --ok-line: rgba(13, 148, 136, .35);
    --ok-fg: #0f766e;
    --shadow-pop: 0 24px 60px -20px rgba(30, 41, 90, .35);
    --shadow-glow: 0 20px 60px -24px rgba(79, 70, 229, .35);
    --sun: none;
    --moon: inline-block;
  }
}

/* ===== base ===== */
* { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }
ul, ol { list-style: none; }
a { color: inherit; text-decoration: none; }
button { font: inherit; }

body {
  font-family: var(--font-body), system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
  background-color: var(--bg);
  color: var(--text);
  line-height: 1.5;
  min-height: 100vh;
  background-image:
    radial-gradient(900px 500px at 8% -10%, var(--glow-1), transparent 60%),
    radial-gradient(700px 420px at 96% 0%, var(--glow-2), transparent 55%),
    radial-gradient(600px 400px at 60% 110%, var(--glow-3), transparent 60%);
  background-attachment: fixed;
  transition: background-color .25s, color .25s;
}

[lang="ar"] body { font-family: var(--font-ar), var(--font-body), system-ui, 'Segoe UI', Tahoma, sans-serif; }
[lang="ar"] .hero h1, [lang="ar"] .brand, [lang="ar"] h2, [lang="ar"] h3,
[lang="ar"] .auth-card h1, [lang="ar"] .cb-title strong, [lang="ar"] .stats strong {
  font-family: var(--font-ar), var(--font-display), sans-serif;
  letter-spacing: 0;
}

:focus-visible { outline: 2px solid var(--accent-text); outline-offset: 3px; border-radius: 8px; }

.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
.skip { position: absolute; inset-inline-start: 12px; top: -60px; z-index: 100; background: var(--accent); color: var(--on-accent); font-weight: 600; padding: 10px 16px; border-radius: 10px; }
.skip:focus { top: 12px; }
.wrap { max-width: 1180px; margin: 0 auto; padding: 0 20px; }

/* ===== header / footer ===== */
.site-header { position: sticky; top: 0; z-index: 30; background: var(--header-bg); backdrop-filter: blur(10px); border-bottom: 1px solid var(--line); }
.site-header .wrap { display: flex; align-items: center; justify-content: space-between; gap: 12px; height: 64px; }
.brand { display: flex; align-items: center; gap: 10px; font-family: var(--font-display), sans-serif; font-weight: 700; font-size: 1.35rem; letter-spacing: -.5px; direction: ltr; }
.brand-mark { width: 28px; height: 28px; border-radius: 9px; color: var(--on-accent); display: grid; place-items: center; background: linear-gradient(135deg, var(--accent), var(--accent2)); }
.brand b { font-weight: 700; background: linear-gradient(90deg, var(--grad-a), var(--grad-b)); -webkit-background-clip: text; background-clip: text; color: transparent; }
.nav { display: flex; gap: 4px; }
.nav a { color: var(--muted); font-size: .92rem; padding: 8px 12px; border-radius: 10px; }
.nav a:hover { color: var(--text); background: var(--panel); }
.header-right { display: flex; align-items: center; gap: 8px; }
.auth-links { display: flex; align-items: center; gap: 6px; }
.site-footer { border-top: 1px solid var(--line); padding: 28px 0; color: var(--muted); font-size: .88rem; }

.icon-btn { display: inline-flex; align-items: center; justify-content: center; gap: 8px; height: 40px; min-width: 40px; padding: 0 12px; border-radius: 12px; cursor: pointer; font-size: .88rem; font-weight: 600; color: var(--text-soft); background: var(--panel); border: 1px solid var(--line); transition: border-color .15s, color .15s; }
.icon-btn:hover { color: var(--text); border-color: var(--hover-line); }
.theme-btn { padding: 0; width: 40px; }
.ti-sun { display: var(--sun); }
.ti-moon { display: var(--moon); }

.btn-ghost, .btn-solid { display: inline-flex; align-items: center; justify-content: center; padding: 8px 16px; border-radius: 12px; font-size: .9rem; font-weight: 600; cursor: pointer; border: 1px solid var(--line); background: transparent; color: var(--text); }
.btn-ghost:hover { background: var(--panel); }
.btn-solid { color: var(--on-accent); border: 0; background: linear-gradient(135deg, var(--accent), var(--accent2)); }
.btn-solid:hover { filter: brightness(1.08); }

/* ===== hero ===== */
.hero { text-align: center; padding-top: 64px; padding-bottom: 36px; }
.eyebrow { display: inline-block; margin-bottom: 18px; padding: 6px 14px; border-radius: 999px; font-size: .78rem; letter-spacing: .14em; text-transform: uppercase; color: var(--accent-text); border: 1px solid var(--chip-line); }
.hero h1 { font-family: var(--font-display), sans-serif; font-weight: 700; font-size: clamp(2.1rem, 5.4vw, 3.8rem); line-height: 1.12; letter-spacing: -.03em; max-width: 880px; margin: 0 auto; overflow-wrap: anywhere; }
.hero h1 em { font-style: normal; color: transparent; background: linear-gradient(90deg, var(--grad-a), var(--grad-b) 55%, var(--grad-c)); -webkit-background-clip: text; background-clip: text; }
.sub { color: var(--muted); max-width: 620px; margin: 16px auto 30px; font-size: 1.05rem; }

/* ===== search bar ===== */
.searchbar { position: relative; display: flex; gap: 10px; max-width: 760px; margin: 0 auto; padding: 8px; border-radius: 22px; background: var(--glass); border: 1px solid var(--line); box-shadow: var(--shadow-glow); transition: border-color .2s, box-shadow .2s; }
.searchbar:focus-within { border-color: var(--hover-line); box-shadow: 0 0 0 4px var(--focus-ring), var(--shadow-glow); }
.field { flex: 1; display: flex; align-items: center; gap: 10px; padding: 0 12px; min-width: 0; }
.field svg { flex: none; color: var(--muted); }
.field input { flex: 1; min-width: 0; background: none; border: 0; outline: 0; color: var(--text); font: inherit; font-size: 1.05rem; padding: 14px 0; text-align: start; }
.field input::placeholder { color: var(--placeholder); }
.clear { background: none; border: 0; color: var(--muted); cursor: pointer; font-size: 1.5rem; line-height: 1; padding: 4px 8px; border-radius: 8px; }
.clear:hover { color: var(--text); }
.go { min-width: 112px; padding: 0 28px; border: 0; border-radius: 16px; cursor: pointer; font-weight: 700; color: var(--on-accent); background: linear-gradient(135deg, var(--accent), var(--accent2)); display: inline-grid; place-items: center; transition: transform .15s, filter .15s; }
.go:hover { filter: brightness(1.08); }
.go:active { transform: scale(.98); }
.go:disabled { opacity: .85; cursor: progress; }
.spinner { width: 18px; height: 18px; border-radius: 50%; display: inline-block; border: 2px solid rgba(6, 16, 31, .3); border-top-color: var(--on-accent); animation: spin .7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.suggest { position: absolute; inset-inline: 0; top: calc(100% + 10px); z-index: 40; text-align: start; max-height: 420px; overflow: auto; padding: 8px; background: var(--surface); border: 1px solid var(--line); border-radius: 18px; box-shadow: var(--shadow-pop); }
.sg-group { padding: 10px 12px 4px; font-size: .72rem; letter-spacing: .12em; text-transform: uppercase; color: var(--muted); }
.sg-item { display: flex; align-items: center; gap: 12px; padding: 10px 12px; border-radius: 12px; cursor: pointer; }
.sg-item svg { flex: none; color: var(--muted); }
.sg-item[aria-selected="true"] { background: var(--select-bg); }
.sg-item mark { background: none; color: var(--accent-text); font-weight: 700; }
.sg-label { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sg-remove { flex: none; width: 28px; height: 28px; border-radius: 8px; border: 0; cursor: pointer; background: transparent; color: var(--muted); font-size: 1.25rem; line-height: 1; opacity: 0; transition: opacity .15s, background .15s; }
.sg-item:hover .sg-remove, .sg-item[aria-selected="true"] .sg-remove { opacity: 1; }
.sg-remove:hover { background: var(--new-bg); color: var(--new-fg); }
@media (hover: none) { .sg-remove { opacity: 1; } }
.sg-foot { padding: 8px 12px 4px; border-top: 1px solid var(--line); margin-top: 6px; }
.sg-foot button { background: none; border: 0; color: var(--muted); font-size: .85rem; cursor: pointer; text-decoration: underline; }

/* ===== trending, stats, platforms ===== */
.trending { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; align-items: center; max-width: 760px; margin: 20px auto 0; }
.trending span { color: var(--muted); font-size: .85rem; }
.trending a { display: inline-block; padding: 6px 14px; border-radius: 999px; font-size: .86rem; color: var(--text-soft); background: var(--panel); border: 1px solid var(--line); }
.trending a:hover { border-color: var(--hover-line); color: var(--text); }
.stats { display: flex; gap: 38px; flex-wrap: wrap; justify-content: center; margin-top: 34px; }
.stats strong { display: block; font-family: var(--font-display), sans-serif; font-size: 1.7rem; font-variant-numeric: tabular-nums; }
.stats span { color: var(--muted); font-size: .78rem; text-transform: uppercase; letter-spacing: .1em; }

.platforms { text-align: center; padding-bottom: 8px; }
.platforms h2 { font-size: .78rem; letter-spacing: .14em; text-transform: uppercase; color: var(--muted); font-weight: 600; margin-bottom: 12px; }
.platforms ul { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; }
.plat { display: inline-flex; align-items: center; gap: 8px; padding: 8px 16px; border-radius: 999px; font-size: .9rem; font-weight: 600; background: var(--panel); border: 1px solid var(--line); }
a.plat:hover { border-color: var(--hover-line); }
.plat em { font-style: normal; font-weight: 500; font-size: .78rem; color: var(--muted); font-variant-numeric: tabular-nums; }
.plat.off { opacity: .45; font-weight: 500; }

/* ===== results layout, filters ===== */
.results-layout { display: grid; grid-template-columns: 270px minmax(0, 1fr); gap: 28px; padding-top: 20px; padding-bottom: 80px; align-items: start; scroll-margin-top: 80px; }
.filters-wrap { position: sticky; top: 84px; }
.filters-btn { display: none; }
.filters { background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius); padding: 6px 18px 12px; }
.filters section { padding: 14px 0; border-bottom: 1px solid var(--line); }
.filters section:last-child { border-bottom: 0; }
.filters h3 { font-size: .74rem; font-weight: 600; text-transform: uppercase; letter-spacing: .12em; color: var(--muted); margin-bottom: 8px; }
.opt { display: flex; align-items: center; gap: 10px; margin-inline: -8px; padding: 7px 8px; border-radius: 10px; font-size: .92rem; color: var(--text-soft); }
.opt:hover { background: var(--panel-strong); }
.box { flex: none; width: 18px; height: 18px; border-radius: 6px; display: grid; place-items: center; border: 1.5px solid var(--muted); font-size: .7rem; font-weight: 700; color: var(--on-accent); }
.opt.selected .box { background: var(--accent); border-color: var(--accent); }
.opt-label { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.opt-count { font-size: .78rem; color: var(--muted); font-variant-numeric: tabular-nums; }

.results-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-bottom: 14px; }
.results-head h2 { font-family: var(--font-display), sans-serif; font-size: 1.3rem; }
.sort { display: flex; gap: 4px; padding: 4px; border-radius: 12px; background: var(--panel); border: 1px solid var(--line); }
.sort a { padding: 6px 14px; border-radius: 9px; font-size: .88rem; color: var(--muted); }
.sort a[aria-current="true"] { background: var(--select-bg); color: var(--text); }

.active { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; margin-bottom: 16px; }
.active-list { display: flex; flex-wrap: wrap; gap: 8px; }
.chipx { display: inline-flex; align-items: center; gap: 8px; padding: 6px 12px; border-radius: 999px; font-size: .85rem; background: var(--chip-bg); border: 1px solid var(--chip-line); }
.chipx:hover { filter: brightness(1.1); }
.clear-all { color: var(--muted); font-size: .85rem; text-decoration: underline; text-underline-offset: 3px; }

/* ===== cards ===== */
.grid { display: grid; gap: 16px; grid-template-columns: repeat(auto-fill, minmax(290px, 1fr)); }
.card { position: relative; display: flex; flex-direction: column; gap: 8px; padding: 20px; border-radius: var(--radius); background: var(--panel); border: 1px solid var(--line); transition: transform .2s, border-color .2s, background .2s; }
.card:hover, .card:focus-within { transform: translateY(-3px); border-color: var(--hover-line); background: var(--panel-hover); }
.card-top { display: flex; align-items: center; gap: 8px; font-size: .75rem; color: var(--muted); flex-wrap: wrap; }
.card-top time { margin-inline-start: auto; }
.badge, .new, .remote { padding: 3px 10px; border-radius: 999px; font-size: .68rem; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; }
.badge { background: var(--badge-bg); color: var(--badge-fg); }
.new { background: var(--new-bg); color: var(--new-fg); }
.remote { background: var(--remote-bg); color: var(--remote-fg); }
.card h3 { font-family: var(--font-display), sans-serif; font-size: 1.08rem; line-height: 1.3; overflow-wrap: anywhere; }
.card h3 a::after { content: ''; position: absolute; inset: 0; border-radius: var(--radius); }
.card h3 a:hover { color: var(--accent-text); }
.meta { color: var(--text-soft); font-size: .9rem; }
.excerpt { color: var(--muted); font-size: .88rem; display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; overflow: hidden; }
.tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: auto; padding-top: 6px; }
.tag { max-width: 100%; padding: 3px 9px; border-radius: 8px; font-size: .72rem; color: var(--text-soft); background: var(--panel-strong); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* ===== pagination, empty ===== */
.pager { display: flex; flex-wrap: wrap; justify-content: center; align-items: center; gap: 6px; margin-top: 34px; }
.pager ol { display: flex; flex-wrap: wrap; gap: 6px; justify-content: center; }
.pager a, .pager .pg { min-width: 40px; height: 40px; padding: 0 12px; display: inline-grid; place-items: center; border-radius: 12px; font-size: .9rem; background: var(--panel); border: 1px solid var(--line); }
.pager a:hover { border-color: var(--hover-line); }
.pager [aria-current="page"] { background: linear-gradient(135deg, var(--accent), var(--accent2)); color: var(--on-accent); border-color: transparent; font-weight: 700; }
.pager [aria-disabled="true"] { opacity: .35; }

.empty { text-align: center; padding: 56px 20px; border: 1px dashed var(--line); border-radius: var(--radius); }
.empty h3 { font-family: var(--font-display), sans-serif; font-size: 1.3rem; margin-bottom: 6px; }
.empty p { color: var(--muted); }
.empty .trending { margin: 18px auto; }
.btn-link { display: inline-block; margin-top: 16px; padding: 10px 22px; border-radius: 12px; font-weight: 600; color: var(--on-accent); background: linear-gradient(135deg, var(--accent), var(--accent2)); }

/* ===== account menu, auth ===== */
.usermenu { position: relative; }
.usermenu summary { list-style: none; cursor: pointer; display: flex; align-items: center; gap: 10px; padding: 4px 12px 4px 4px; border-radius: 999px; border: 1px solid var(--line); background: var(--panel); }
[dir="rtl"] .usermenu summary { padding: 4px 4px 4px 12px; }
.usermenu summary::-webkit-details-marker { display: none; }
.avatar { width: 30px; height: 30px; border-radius: 50%; display: grid; place-items: center; font-weight: 700; font-size: .85rem; color: var(--on-accent); background: linear-gradient(135deg, var(--accent), var(--accent2)); }
.uname { max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: .9rem; }
.usermenu-panel { position: absolute; inset-inline-end: 0; top: calc(100% + 8px); min-width: 230px; padding: 8px; border-radius: 16px; background: var(--surface); border: 1px solid var(--line); box-shadow: var(--shadow-pop); z-index: 50; }
.usermenu-panel .who { padding: 8px 10px 10px; border-bottom: 1px solid var(--line); margin-bottom: 6px; font-size: .82rem; color: var(--muted); overflow-wrap: anywhere; }
.usermenu-panel a, .usermenu-panel button { display: block; width: 100%; text-align: start; padding: 9px 10px; border-radius: 10px; font-size: .92rem; background: none; border: 0; color: var(--text); cursor: pointer; }
.usermenu-panel a:hover, .usermenu-panel button:hover { background: var(--panel-strong); }

.auth-wrap { min-height: calc(100vh - 220px); display: grid; place-items: center; padding: 48px 20px; }
.auth-card { width: 100%; max-width: 440px; padding: 34px 30px; border-radius: 24px; background: var(--glass); border: 1px solid var(--line); box-shadow: var(--shadow-glow); }
.auth-card h1 { font-family: var(--font-display), sans-serif; font-size: 1.7rem; letter-spacing: -.02em; }
.auth-card .lead { color: var(--muted); margin: 6px 0 24px; font-size: .95rem; overflow-wrap: anywhere; }
.auth-form { display: grid; gap: 16px; }
.fld label { display: block; font-size: .85rem; font-weight: 600; margin-bottom: 6px; color: var(--text-soft); }
.fld input { width: 100%; padding: 13px 14px; border-radius: 12px; border: 1px solid var(--line); background: var(--panel-strong); color: var(--text); font: inherit; outline: none; transition: border-color .2s, box-shadow .2s; }
.fld input:focus { border-color: var(--hover-line); box-shadow: 0 0 0 4px var(--focus-ring); }
.fld input[aria-invalid="true"] { border-color: #f87171; }
.fld .hint { margin-top: 6px; font-size: .78rem; color: var(--muted); }
.fld .err { margin-top: 6px; font-size: .82rem; color: var(--danger-text); }
.pw { position: relative; }
.pw input { padding-inline-end: 76px; }
.pw button { position: absolute; inset-inline-end: 8px; top: 50%; transform: translateY(-50%); padding: 6px 10px; border-radius: 8px; border: 0; background: var(--panel-strong); color: var(--muted); font-size: .78rem; cursor: pointer; }
.alert { padding: 12px 14px; border-radius: 12px; font-size: .9rem; background: var(--danger-bg); border: 1px solid var(--danger-line); color: var(--danger-fg); }
.alert.ok { background: var(--ok-bg); border-color: var(--ok-line); color: var(--ok-fg); }
.auth-submit { width: 100%; padding: 14px; border: 0; border-radius: 14px; font-weight: 700; font-size: 1rem; color: var(--on-accent); cursor: pointer; background: linear-gradient(135deg, var(--accent), var(--accent2)); }
.auth-submit:disabled { opacity: .7; cursor: progress; }
.auth-foot { margin-top: 22px; text-align: center; font-size: .9rem; color: var(--muted); }
.auth-foot a { color: var(--accent-text); text-decoration: underline; text-underline-offset: 3px; }

/* ===== chatbot ===== */
.cb-launch { position: fixed; inset-inline-end: 20px; bottom: calc(20px + env(safe-area-inset-bottom, 0px)); z-index: 70; width: 60px; height: 60px; border-radius: 50%; border: 0; cursor: pointer; display: grid; place-items: center; color: var(--on-accent); background: linear-gradient(135deg, var(--accent), var(--accent2)); box-shadow: 0 14px 40px -10px rgba(94, 234, 212, .55), 0 6px 20px rgba(0, 0, 0, .35); transition: transform .15s, filter .15s; }
.cb-launch:hover { transform: translateY(-2px) scale(1.04); filter: brightness(1.06); }

.cb-panel { position: fixed; inset-inline-end: 20px; bottom: calc(92px + env(safe-area-inset-bottom, 0px)); z-index: 70; width: min(400px, calc(100vw - 24px)); height: min(620px, calc(100vh - 130px)); display: flex; flex-direction: column; overflow: hidden; border-radius: 22px; background: var(--surface-2); border: 1px solid var(--line); box-shadow: var(--shadow-pop); animation: cb-in .18s ease-out; }
@keyframes cb-in { from { opacity: 0; transform: translateY(10px) scale(.98); } to { opacity: 1; transform: none; } }
.cb-head { display: flex; align-items: center; gap: 12px; padding: 14px; border-bottom: 1px solid var(--line); background: linear-gradient(135deg, var(--chip-bg), var(--select-bg)); }
.cb-avatar { width: 38px; height: 38px; border-radius: 12px; display: grid; place-items: center; color: var(--on-accent); background: linear-gradient(135deg, var(--accent), var(--accent2)); }
.cb-avatar svg { width: 22px; height: 22px; }
.cb-title { flex: 1; min-width: 0; display: flex; flex-direction: column; line-height: 1.25; }
.cb-title strong { font-family: var(--font-display), sans-serif; font-size: 1rem; }
.cb-title span { font-size: .76rem; color: var(--muted); }
.cb-icon { border: 0; cursor: pointer; min-width: 34px; height: 34px; padding: 0 10px; border-radius: 10px; display: grid; place-items: center; font-size: .8rem; color: var(--muted); background: var(--panel-strong); }
.cb-icon:hover { color: var(--text); }

.cb-body { flex: 1; overflow-y: auto; padding: 16px 14px; display: flex; flex-direction: column; gap: 12px; scroll-behavior: smooth; }
.cb-row { display: flex; }
.cb-row.user { justify-content: flex-end; }
.cb-bubble { max-width: 88%; padding: 11px 14px; border-radius: 16px; border-end-start-radius: 4px; font-size: .92rem; line-height: 1.55; background: var(--panel-strong); border: 1px solid var(--line); overflow-wrap: anywhere; }
.cb-bubble p + p { margin-top: 8px; }
.cb-bubble.user { border: 0; border-end-start-radius: 16px; border-end-end-radius: 4px; color: var(--on-accent); font-weight: 500; background: linear-gradient(135deg, var(--accent), var(--accent2)); }
.cb-jobs { display: grid; gap: 8px; margin-top: 12px; }
.cb-job { display: grid; gap: 2px; padding: 10px 12px; border-radius: 12px; background: var(--surface); border: 1px solid var(--line); transition: border-color .15s, transform .15s; }
a.cb-job:hover { border-color: var(--hover-line); transform: translateY(-1px); }
.cb-job-title { font-weight: 600; font-size: .9rem; line-height: 1.3; }
.cb-job-meta { font-size: .8rem; color: var(--muted); }
.cb-job-foot { display: flex; align-items: center; gap: 8px; margin-top: 4px; }
.cb-job-tag { padding: 2px 9px; border-radius: 999px; font-size: .68rem; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; background: var(--badge-bg); color: var(--badge-fg); }
.cb-match { padding: 2px 9px; border-radius: 999px; font-size: .7rem; font-weight: 700; background: var(--remote-bg); color: var(--remote-fg); }
.cb-more { display: inline-block; margin-top: 12px; font-size: .85rem; font-weight: 600; color: var(--accent-text); }
.cb-more:hover { text-decoration: underline; text-underline-offset: 3px; }
.cb-note { margin-top: 8px; font-size: .78rem; color: var(--muted); }
.cb-suggest { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 4px; }
.cb-suggest button { cursor: pointer; padding: 8px 14px; border-radius: 999px; font-size: .84rem; color: var(--text-soft); background: var(--panel); border: 1px solid var(--line); }
.cb-suggest button:hover { border-color: var(--hover-line); color: var(--text); }
.cb-typing { display: flex; gap: 5px; align-items: center; padding: 14px; }
.cb-typing span { width: 7px; height: 7px; border-radius: 50%; background: var(--muted); animation: cb-dot 1s infinite ease-in-out; }
.cb-typing span:nth-child(2) { animation-delay: .15s; }
.cb-typing span:nth-child(3) { animation-delay: .3s; }
@keyframes cb-dot { 0%, 80%, 100% { opacity: .3; transform: translateY(0); } 40% { opacity: 1; transform: translateY(-3px); } }

.cb-form { display: flex; gap: 8px; padding: 12px; border-top: 1px solid var(--line); background: var(--surface); }
.cb-form input { flex: 1; min-width: 0; padding: 12px 14px; border-radius: 14px; border: 1px solid var(--line); background: var(--panel-strong); color: var(--text); font: inherit; font-size: .92rem; outline: none; }
.cb-form input:focus { border-color: var(--hover-line); box-shadow: 0 0 0 3px var(--focus-ring); }
.cb-form button { width: 46px; border: 0; border-radius: 14px; cursor: pointer; display: grid; place-items: center; color: var(--on-accent); background: linear-gradient(135deg, var(--accent), var(--accent2)); }
.cb-form button:disabled { opacity: .4; cursor: not-allowed; }
[dir="rtl"] .cb-send { transform: scaleX(-1); }

.cb-connect { display: grid; gap: 12px; padding: 4px 2px; }
.cb-connect h3 { font-family: var(--font-display), sans-serif; font-size: 1.15rem; }
.cb-connect p { font-size: .88rem; line-height: 1.6; color: var(--muted); }
.cb-connect input { width: 100%; padding: 13px 14px; border-radius: 12px; border: 1px solid var(--line); background: var(--panel-strong); color: var(--text); font: inherit; outline: none; text-align: start; }
.cb-connect input:focus { border-color: var(--hover-line); box-shadow: 0 0 0 3px var(--focus-ring); }
.cb-connect button { padding: 13px; border: 0; border-radius: 12px; font-weight: 700; cursor: pointer; color: var(--on-accent); background: linear-gradient(135deg, var(--accent), var(--accent2)); }
.cb-connect button:disabled { opacity: .5; cursor: not-allowed; }
.cb-connect a { font-size: .85rem; color: var(--accent-text); text-decoration: underline; text-underline-offset: 3px; }
.cb-error { padding: 10px 12px; border-radius: 10px; font-size: .85rem; background: var(--danger-bg); border: 1px solid var(--danger-line); color: var(--danger-fg) !important; }

/* ===== responsive ===== */
@media (max-width: 900px) {
  .hero { padding-top: 40px; }
  .results-layout { grid-template-columns: 1fr; }
  .filters-wrap { position: static; }
  .filters-btn { display: inline-flex; align-items: center; gap: 8px; padding: 10px 18px; border-radius: 12px; cursor: pointer; color: var(--text); background: var(--panel); border: 1px solid var(--line); }
  .badge-count { min-width: 22px; height: 22px; border-radius: 999px; display: grid; place-items: center; font-size: .75rem; font-weight: 700; color: var(--on-accent); background: var(--accent); }
  .filters-panel { display: none; margin-top: 12px; }
  .filters-panel.open { display: block; }
  .searchbar { flex-direction: column; }
  .go { min-height: 48px; }
}

@media (max-width: 700px) {
  .nav { display: none; }
  .uname { display: none; }
  .usermenu summary, [dir="rtl"] .usermenu summary { padding: 4px; }
  .lang-btn span { display: none; }
  .lang-btn { padding: 0; width: 40px; }
}

@media (max-width: 520px) {
  .cb-panel { inset-inline: 12px; width: auto; bottom: calc(86px + env(safe-area-inset-bottom, 0px)); height: calc(100vh - 110px); }
  .cb-launch { inset-inline-end: 14px; bottom: calc(14px + env(safe-area-inset-bottom, 0px)); }
}

@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; transition: none !important; scroll-behavior: auto !important; }
}
'''

# =====================================================================
# BACKEND: locale, auth and chat messages
# =====================================================================

FILES[BACK / "app/Http/Controllers/Controller.php"] = r'''<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;

abstract class Controller
{
    /** Use the website language (sent by Next.js in X-Locale) for validation errors and chat replies. */
    protected function applyLocale(Request $request): string
    {
        $locale = $request->header('X-Locale') === 'ar' ? 'ar' : 'en';
        app()->setLocale($locale);

        return $locale;
    }
}
'''

FILES[BACK / "app/Http/Controllers/AuthController.php"] = r'''<?php

namespace App\Http\Controllers;

use App\Models\User;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\RateLimiter;
use Illuminate\Support\Str;
use Illuminate\Validation\Rules\Password;
use Illuminate\Validation\ValidationException;

class AuthController extends Controller
{
    private const TOKEN_DAYS = 30;

    public function register(Request $request): JsonResponse
    {
        $this->applyLocale($request);
        $request->merge(['email' => Str::lower(trim((string) $request->input('email')))]);

        $data = $request->validate([
            'name'     => ['required', 'string', 'min:2', 'max:100'],
            'email'    => ['required', 'string', 'email:rfc', 'max:255', 'unique:users,email'],
            'password' => ['required', 'string', 'confirmed', Password::min(8)->letters()->numbers()],
        ]);

        $user = User::create([
            'name'     => trim($data['name']),
            'email'    => $data['email'],
            'password' => $data['password'], // hashed by the model cast
        ]);

        return $this->issueToken($user, 201);
    }

    public function login(Request $request): JsonResponse
    {
        $this->applyLocale($request);
        $request->merge(['email' => Str::lower(trim((string) $request->input('email')))]);

        $data = $request->validate([
            'email'    => ['required', 'string', 'email'],
            'password' => ['required', 'string'],
        ]);

        $key = 'login:' . $data['email'] . '|' . $request->ip();

        if (RateLimiter::tooManyAttempts($key, 5)) {
            $seconds = RateLimiter::availableIn($key);

            throw ValidationException::withMessages([
                'email' => [__('Too many attempts. Try again in :seconds seconds.', ['seconds' => $seconds])],
            ])->status(429);
        }

        $user = User::where('email', $data['email'])->first();

        if (!$user || !Hash::check($data['password'], $user->password)) {
            RateLimiter::hit($key, 60);

            throw ValidationException::withMessages([
                'email' => [__('These credentials do not match our records.')],
            ]);
        }

        RateLimiter::clear($key);

        return $this->issueToken($user);
    }

    public function me(Request $request): JsonResponse
    {
        return response()->json(['user' => $this->present($request->user())]);
    }

    public function logout(Request $request): JsonResponse
    {
        $request->user()->currentAccessToken()->delete();

        return response()->json(['message' => 'Logged out.']);
    }

    public function updatePassword(Request $request): JsonResponse
    {
        $this->applyLocale($request);

        $data = $request->validate([
            'current_password' => ['required', 'string'],
            'password'         => [
                'required', 'string', 'confirmed', 'different:current_password',
                Password::min(8)->letters()->numbers(),
            ],
        ]);

        $user = $request->user();

        if (!Hash::check($data['current_password'], $user->password)) {
            throw ValidationException::withMessages([
                'current_password' => [__('Your current password is incorrect.')],
            ]);
        }

        $user->forceFill(['password' => $data['password']])->save();

        // Sign out every other device; keep this session.
        $current = $user->currentAccessToken();
        $user->tokens()->where('id', '!=', $current->id)->delete();

        return response()->json(['message' => 'Password updated.']);
    }

    private function issueToken(User $user, int $status = 200): JsonResponse
    {
        $token = $user->createToken('web', ['*'], now()->addDays(self::TOKEN_DAYS));

        return response()->json([
            'user'       => $this->present($user),
            'token'      => $token->plainTextToken,
            'expires_at' => $token->accessToken->expires_at?->toIso8601String(),
        ], $status);
    }

    private function present(User $user): array
    {
        return ['id' => $user->id, 'name' => $user->name, 'email' => $user->email];
    }
}
'''

FILES[BACK / "app/Http/Controllers/ChatController.php"] = r'''<?php

namespace App\Http\Controllers;

use App\Services\Chat\JobAssistant;
use App\Services\Chat\OpenAIException;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\RateLimiter;

class ChatController extends Controller
{
    public function message(Request $request): JsonResponse
    {
        // The assistant answers in the website language, whatever language the user types in.
        $this->applyLocale($request);

        $apiKey = trim((string) $request->header('X-OpenAI-Key', ''));

        if ($apiKey === '' || strlen($apiKey) > 300 || preg_match('/\s/', $apiKey)) {
            return response()->json([
                'code'  => 'key_required',
                'reply' => __('Please connect your OpenAI API key to chat.'),
            ], 401);
        }

        $data = $request->validate([
            'message'        => ['required', 'string', 'max:500'],
            'history'        => ['nullable', 'array', 'max:12'],
            'history.*.role' => ['required', 'string', 'in:user,bot'],
            'history.*.text' => ['required', 'string', 'max:1000'],
            'last_search'    => ['nullable', 'array'],
        ]);

        // Per API key (the Next.js server is the only direct caller, so per-IP would be shared).
        $limiterKey = 'chat:' . hash('sha256', $apiKey);
        if (RateLimiter::tooManyAttempts($limiterKey, (int) config('chat.rate_per_min', 20))) {
            return response()->json([
                'code'  => 'rate_limited',
                'reply' => __('You are sending messages too quickly. Please wait a few seconds.'),
            ], 429);
        }
        RateLimiter::hit($limiterKey, 60);

        try {
            $result = JobAssistant::make()->handle(
                $apiKey,
                trim($data['message']),
                $data['history'] ?? [],
                $data['last_search'] ?? null
            );

            return response()->json($result);
        } catch (OpenAIException $e) {
            [$code, $reply, $status] = match ($e->reason) {
                'invalid_key'  => ['invalid_key', __('OpenAI rejected this API key. Please check it and connect again.'), 401],
                'quota'        => ['quota', __('This OpenAI account has no remaining credit or has reached its spending limit. Add credit in your OpenAI billing settings, then try again.'), 402],
                'rate_limited' => ['upstream_rate_limited', __('OpenAI is rate limiting this key right now. Please try again in a minute.'), 429],
                'model'        => ['model_unavailable', __('The AI model configured on this site is not available for your OpenAI key. The site owner can change OPENAI_CHAT_MODEL.'), 503],
                'forbidden'    => ['forbidden', __('OpenAI denied access for this key (for example a restricted key or an unsupported region).'), 403],
                default        => ['upstream', __('The AI service is not responding right now. Please try again in a moment.'), 502],
            };

            return response()->json(['code' => $code, 'reply' => $reply], $status);
        } catch (\Throwable $e) {
            report($e);

            return response()->json([
                'code'  => 'error',
                'reply' => __('Something went wrong on our side. Please try again.'),
            ], 500);
        }
    }
}
'''

FILES[BACK / "lang/ar.json"] = r'''{
    "These credentials do not match our records.": "بيانات الدخول غير صحيحة.",
    "Too many attempts. Try again in :seconds seconds.": "محاولات كثيرة. حاول مرة أخرى بعد :seconds ثانية.",
    "Your current password is incorrect.": "كلمة المرور الحالية غير صحيحة.",
    "Please connect your OpenAI API key to chat.": "يرجى ربط مفتاح OpenAI API للدردشة.",
    "You are sending messages too quickly. Please wait a few seconds.": "ترسل الرسائل بسرعة كبيرة. يرجى الانتظار بضع ثوانٍ.",
    "OpenAI rejected this API key. Please check it and connect again.": "رفضت OpenAI مفتاح API هذا. تحقق منه ثم اربطه مرة أخرى.",
    "This OpenAI account has no remaining credit or has reached its spending limit. Add credit in your OpenAI billing settings, then try again.": "لا يوجد رصيد متبقٍ في حساب OpenAI هذا أو تم بلوغ حد الإنفاق. أضف رصيدًا من إعدادات الفوترة في OpenAI ثم حاول مرة أخرى.",
    "OpenAI is rate limiting this key right now. Please try again in a minute.": "تقوم OpenAI بتقييد معدل الطلبات لهذا المفتاح حاليًا. يرجى المحاولة بعد دقيقة.",
    "The AI model configured on this site is not available for your OpenAI key. The site owner can change OPENAI_CHAT_MODEL.": "نموذج الذكاء الاصطناعي المضبوط على هذا الموقع غير متاح لمفتاح OpenAI الخاص بك. يمكن لمالك الموقع تغيير OPENAI_CHAT_MODEL.",
    "OpenAI denied access for this key (for example a restricted key or an unsupported region).": "رفضت OpenAI الوصول لهذا المفتاح (مثلًا مفتاح مقيّد أو منطقة غير مدعومة).",
    "The AI service is not responding right now. Please try again in a moment.": "خدمة الذكاء الاصطناعي لا تستجيب حاليًا. يرجى المحاولة مرة أخرى بعد قليل.",
    "Something went wrong on our side. Please try again.": "حدث خطأ من جانبنا. يرجى المحاولة مرة أخرى.",
    "How can I help you find a job?": "كيف يمكنني مساعدتك في العثور على وظيفة؟",
    "What kind of job are you looking for? A title, a skill or a city helps.": "ما نوع الوظيفة التي تبحث عنها؟ يساعد ذكر المسمى الوظيفي أو المهارة أو المدينة.",
    "I could not find strong matches. Try a broader title, another city, or remove a filter.": "لم أجد نتائج مطابقة بقوة. جرّب مسمى وظيفيًا أوسع أو مدينة أخرى أو أزل أحد عوامل التصفية.",
    "I found 1 matching job. The best match is “:title” at :company.": "وجدت وظيفة واحدة مطابقة. أفضل نتيجة هي «:title» لدى :company.",
    "I found :count matching jobs. The best match is “:title” at :company.": "وجدت :count وظيفة مطابقة. أفضل نتيجة هي «:title» لدى :company."
}
'''

FILES[BACK / "lang/ar/validation.php"] = r'''<?php

// Partial Arabic file: any rule not listed here falls back to Laravel's English message.
return [
    'required'  => 'حقل :attribute مطلوب.',
    'string'    => 'يجب أن يكون :attribute نصًا.',
    'email'     => 'يجب أن يكون :attribute بريدًا إلكترونيًا صالحًا.',
    'unique'    => ':attribute مستخدم بالفعل.',
    'confirmed' => 'تأكيد :attribute غير متطابق.',
    'different' => 'يجب أن يختلف :attribute عن :other.',
    'in'        => 'القيمة المحددة في :attribute غير صالحة.',
    'array'     => 'يجب أن يكون :attribute قائمة.',
    'integer'   => 'يجب أن يكون :attribute عددًا صحيحًا.',
    'max'       => [
        'string' => 'يجب ألا يزيد :attribute عن :max حرفًا.',
        'array'  => 'يجب ألا يحتوي :attribute على أكثر من :max عناصر.',
    ],
    'min'       => [
        'string' => 'يجب ألا يقل :attribute عن :min أحرف.',
    ],
    'password'  => [
        'letters'       => 'يجب أن تحتوي :attribute على حرف واحد على الأقل.',
        'mixed'         => 'يجب أن تحتوي :attribute على حرف كبير وحرف صغير على الأقل.',
        'numbers'       => 'يجب أن تحتوي :attribute على رقم واحد على الأقل.',
        'symbols'       => 'يجب أن تحتوي :attribute على رمز واحد على الأقل.',
        'uncompromised' => ':attribute ظهرت في تسريب بيانات. يرجى اختيار :attribute مختلفة.',
    ],
    'attributes' => [
        'name'                  => 'الاسم',
        'email'                 => 'البريد الإلكتروني',
        'password'              => 'كلمة المرور',
        'password_confirmation' => 'تأكيد كلمة المرور',
        'current_password'      => 'كلمة المرور الحالية',
        'message'               => 'الرسالة',
    ],
];
'''

# =====================================================================
# Apply: write files, then patch JobAssistant.php (verified first)
# =====================================================================

assistant_path = BACK / "app/Services/Chat/JobAssistant.php"
assistant_text = assistant_path.read_text(encoding="utf-8")
assistant_new = assistant_text

PATCHES = [
    (r"""['{{DATE}}', '{{PREVIOUS}}'],""",
     r"""['{{DATE}}', '{{PREVIOUS}}', '{{LANGUAGE}}'],"""),
    (r"""[date('Y-m-d'), $previous ? json_encode($previous, JSON_UNESCAPED_UNICODE) : 'none'],""",
     r"""[date('Y-m-d'), $previous ? json_encode($previous, JSON_UNESCAPED_UNICODE) : 'none', $this->languageName()],"""),
    (r'''Language: write "reply" in the language of the user's latest message. Write every other text field in English, translating from the user's language when needed.''',
     r'''Language: write "reply" in {{LANGUAGE}}, whatever language the user writes in. Write every other text field in English, translating from the user's language when needed.'''),
    (r'''- "reply": 1 to 3 short sentences, in the language of user_message.''',
     r'''- "reply": 1 to 3 short sentences, in {{LANGUAGE}}.'''),
    (r'''written as search requests in the language of user_message''',
     r'''written as search requests in {{LANGUAGE}}'''),
    (r"""['role' => 'system', 'content' => self::COMPOSER],""",
     r"""['role' => 'system', 'content' => str_replace('{{LANGUAGE}}', $this->languageName(), self::COMPOSER)],"""),
    (r"""$plan['reply'] !== '' ? $plan['reply'] : 'How can I help you find a job?',""",
     r"""$plan['reply'] !== '' ? $plan['reply'] : __('How can I help you find a job?'),"""),
    (r"""$reply !== '' ? $reply : 'What kind of job are you looking for? A title, a skill or a city helps.',""",
     r"""$reply !== '' ? $reply : __('What kind of job are you looking for? A title, a skill or a city helps.'),"""),
    (r"""$fallback = [$this->template($top, $total), []];""",
     r"""$fallback = [$this->localizedTemplate($top, $total), []];"""),
    (r"""private function template(array $top, int $total): string""",
     r"""private function localizedTemplate(array $top, int $total): string
    {
        if ($total === 0 || !$top) {
            return __('I could not find strong matches. Try a broader title, another city, or remove a filter.');
        }

        $values = ['count' => $total, 'title' => $top[0]['title'], 'company' => $top[0]['company']];

        return $total === 1
            ? __('I found 1 matching job. The best match is “:title” at :company.', $values)
            : __('I found :count matching jobs. The best match is “:title” at :company.', $values);
    }

    /** The website language (set from the X-Locale header) decides the language of every reply. */
    private function languageName(): string
    {
        return app()->getLocale() === 'ar' ? 'Arabic' : 'English';
    }

    private function template(array $top, int $total): string"""),
]

problems = []
if "localizedTemplate" in assistant_text:
    PATCHES = []  # already patched

for old, new in PATCHES:
    if assistant_new.count(old) != 1:
        problems.append(f"JobAssistant.php: expected 1 match, found {assistant_new.count(old)} for: {old[:80]!r}")
    else:
        assistant_new = assistant_new.replace(old, new)

if problems:
    print("Nothing was changed. Problems found:")
    for item in problems:
        print("  -", item)
    print("\nSend me these lines and I will adjust the patch.")
    sys.exit(1)

written = []
for path, content in FILES.items():
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_name(path.name + ".prepatch")
        if not backup.exists():
            shutil.copy2(path, backup)
    path.write_text(content, encoding="utf-8")
    written.append(str(path))

if assistant_new != assistant_text:
    backup = assistant_path.with_name(assistant_path.name + ".prepatch")
    if not backup.exists():
        shutil.copy2(assistant_path, backup)
    assistant_path.write_text(assistant_new, encoding="utf-8")
    written.append(str(assistant_path))

print(f"Installed or updated {len(written)} files:")
for item in written:
    print("  +", item)
print("\nNext: restart both servers (see the instructions), then use the globe and sun/moon buttons in the header.")
