// UI texts for the chat widget. Every key exists in both languages.
export const STRINGS = {
  en: {
    title: 'Job assistant',
    powered: 'Powered by OpenAI',
    newChat: 'New',
    newChatTitle: 'Start a new chat',
    disconnect: 'Disconnect',
    disconnectTitle: 'Remove your API key from this browser',
    close: 'Close chat',
    openLabel: 'Open job assistant',
    closeLabel: 'Close job assistant',
    switchTo: 'العربية',
    switchLabel: 'التبديل إلى العربية',
    loading: 'Loading...',
    welcome:
      'Hi! Tell me what kind of job you want, in your own words and in English or Arabic, and I will find the best matches.',
    suggestions: [
      'Remote Python jobs',
      'Odoo developer jobs',
      'Senior data analyst in Berlin',
      'Jobs posted this week',
    ],
    stages: {
      planning: 'Understanding your request...',
      searching: 'Searching the job index...',
      ranking: 'Ranking the best matches...',
      writing: 'Writing the answer...',
    },
    connectTitle: 'Connect your OpenAI key',
    connectBody:
      'The assistant uses OpenAI to understand your request. Paste your own API key to continue. It is encrypted in a secure cookie, never saved in our database, and you can disconnect at any time.',
    connectHint:
      'The API needs its own prepaid credit. A ChatGPT subscription does not include API credit.',
    keyLabel: 'OpenAI API key',
    keyPlaceholder: 'Paste your OpenAI API key (sk-...)',
    connectButton: 'Connect and continue',
    connecting: 'Checking your key...',
    getKey: 'Get an API key from OpenAI →',
    inputPlaceholder: 'Describe the job you want...',
    inputLabel: 'Your message',
    send: 'Send message',
    typing: 'The assistant is working',
    suggestionsLabel: 'Suggestions',
    followUpsLabel: 'Follow-up suggestions',
    openSearch: 'Open full search →',
    match: (n) => `${n}% match`,
    keywordNote: 'AI index unavailable, so I used keyword search.',
    errors: {
      key_required: 'Please connect your OpenAI API key to chat.',
      invalid_key: 'OpenAI rejected this API key. Check it and connect again.',
      invalid: 'OpenAI rejected this API key. Check it and connect again.',
      format: 'That does not look like an OpenAI API key (it starts with sk-).',
      quota:
        'This OpenAI key has no credit left. Add credit on your OpenAI billing page (a ChatGPT subscription does not include API credit), then connect again.',
      forbidden:
        'This OpenAI key is not allowed to use chat and embeddings. Use a key with access to both.',
      model: 'The AI model is not available for this key or on this site.',
      rate_limited: 'You are sending messages too quickly. Please wait a few seconds.',
      upstream_rate_limited: 'OpenAI is rate limiting this key right now. Please try again in a minute.',
      upstream: 'The AI service is not responding right now. Please try again in a moment.',
      unreachable: 'The search service is not reachable right now.',
      server_secret: 'The server is missing CHAT_COOKIE_SECRET. Add it to jobs-frontend/.env.local and restart.',
      network: 'Sorry, I could not reach the search service. Please try again in a moment.',
      error: 'Something went wrong. Please try again.',
    },
  },

  ar: {
    title: 'مساعد الوظائف',
    powered: 'مدعوم بـ OpenAI',
    newChat: 'جديد',
    newChatTitle: 'ابدأ محادثة جديدة',
    disconnect: 'قطع الاتصال',
    disconnectTitle: 'إزالة مفتاح API من هذا المتصفح',
    close: 'إغلاق المحادثة',
    openLabel: 'افتح مساعد الوظائف',
    closeLabel: 'أغلق مساعد الوظائف',
    switchTo: 'English',
    switchLabel: 'Switch to English',
    loading: 'جارٍ التحميل...',
    welcome:
      'مرحبًا! أخبرني بنوع الوظيفة التي تريدها بكلماتك الخاصة، بالعربية أو الإنجليزية، وسأعثر لك على أفضل النتائج.',
    suggestions: [
      'وظائف بايثون عن بُعد',
      'وظائف مطور Odoo',
      'محلل بيانات خبير في برلين',
      'وظائف نُشرت هذا الأسبوع',
    ],
    stages: {
      planning: 'أحلّل طلبك...',
      searching: 'أبحث في الوظائف...',
      ranking: 'أرتّب أفضل النتائج...',
      writing: 'أكتب الإجابة...',
    },
    connectTitle: 'اربط مفتاح OpenAI الخاص بك',
    connectBody:
      'يستخدم المساعد OpenAI لفهم طلبك. الصق مفتاح API الخاص بك للمتابعة. يُشفَّر المفتاح في ملف تعريف ارتباط آمن ولا يُحفظ في قاعدة بياناتنا، ويمكنك قطع الاتصال في أي وقت.',
    connectHint: 'يحتاج API إلى رصيد مدفوع مسبقًا خاص به، واشتراك ChatGPT لا يتضمن رصيد API.',
    keyLabel: 'مفتاح OpenAI API',
    keyPlaceholder: 'الصق مفتاح OpenAI API (sk-...)',
    connectButton: 'اتصال ومتابعة',
    connecting: 'جارٍ التحقق من المفتاح...',
    getKey: 'احصل على مفتاح API من OpenAI ←',
    inputPlaceholder: 'صف الوظيفة التي تريدها...',
    inputLabel: 'رسالتك',
    send: 'إرسال الرسالة',
    typing: 'المساعد يعمل على طلبك',
    suggestionsLabel: 'اقتراحات',
    followUpsLabel: 'اقتراحات للمتابعة',
    openSearch: 'افتح البحث الكامل ←',
    match: (n) => `تطابق ${n}%`,
    keywordNote: 'فهرس الذكاء الاصطناعي غير متاح، لذلك استخدمت البحث بالكلمات المفتاحية.',
    errors: {
      key_required: 'يرجى ربط مفتاح OpenAI API للمتابعة.',
      invalid_key: 'رفضت OpenAI هذا المفتاح. تحقق منه ثم أعد الربط.',
      invalid: 'رفضت OpenAI هذا المفتاح. تحقق منه ثم أعد الربط.',
      format: 'لا يبدو هذا مفتاح OpenAI صحيحًا (يبدأ المفتاح بـ sk-).',
      quota:
        'لا يوجد رصيد في مفتاح OpenAI هذا. أضف رصيدًا من صفحة الفوترة في حسابك (اشتراك ChatGPT لا يتضمن رصيد API) ثم أعد الربط.',
      forbidden: 'هذا المفتاح غير مصرّح له باستخدام المحادثة والتضمينات. استخدم مفتاحًا يملك صلاحية الاثنين.',
      model: 'نموذج الذكاء الاصطناعي غير متاح لهذا المفتاح أو لهذا الموقع.',
      rate_limited: 'ترسل الرسائل بسرعة كبيرة. انتظر بضع ثوانٍ.',
      upstream_rate_limited: 'تقيّد OpenAI هذا المفتاح حاليًا. حاول مرة أخرى بعد دقيقة.',
      upstream: 'خدمة الذكاء الاصطناعي لا تستجيب الآن. حاول مرة أخرى بعد قليل.',
      unreachable: 'تعذّر الوصول إلى خدمة البحث الآن.',
      server_secret: 'يفتقد الخادم المتغير CHAT_COOKIE_SECRET. أضفه إلى jobs-frontend/.env.local ثم أعد التشغيل.',
      network: 'عذرًا، تعذّر الوصول إلى خدمة البحث. حاول مرة أخرى بعد قليل.',
      error: 'حدث خطأ ما. حاول مرة أخرى.',
    },
  },
};

/** Errors that mean "the API key itself is the problem": send the user back to the connect form. */
export const KEY_PROBLEMS = ['key_required', 'invalid_key', 'invalid', 'format', 'quota', 'forbidden'];

export function errorText(lang, code) {
  const table = (STRINGS[lang] || STRINGS.en).errors;
  return table[code] || table.error;
}

export function initialLang() {
  try {
    const saved = localStorage.getItem('hirelume:chat:lang');
    if (saved === 'ar' || saved === 'en') return saved;
  } catch {}
  try {
    if ((navigator.language || '').toLowerCase().startsWith('ar')) return 'ar';
  } catch {}
  return 'en';
}
