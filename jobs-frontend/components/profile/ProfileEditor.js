"use client";

import { useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import Avatar from './Avatar';

const API = '/profile-api/profile';
const MAX_PHOTO = 3 * 1024 * 1024;
const MAX_CV = 5 * 1024 * 1024;
const LABELS = {
  name: 'name', phone: 'phone', headline: 'headline', location: 'location', summary: 'summary',
  skills: 'skills', birth_date: 'birth date', national_number: 'national number',
};

async function call(path, options = {}) {
  try {
    const res = await fetch(`${API}${path}`, { credentials: 'same-origin', ...options });
    if (res.status === 401) { window.location.assign('/login?next=%2Faccount%2Fprofile'); return { ok: false, errors: {}, message: '' }; }
    const data = await res.json().catch(() => null);
    if (res.ok) return { ok: true, data };
    const errors = {};
    for (const [key, value] of Object.entries(data?.errors ?? {})) errors[key] = Array.isArray(value) ? value[0] : String(value);
    const message = res.status === 413
      ? 'That file is too large.'
      : Object.values(errors)[0] || data?.message || 'Something went wrong. Please try again.';
    return { ok: false, errors, message };
  } catch {
    return { ok: false, errors: {}, message: 'Network problem. Check your connection and try again.' };
  }
}

const toForm = (p) => ({
  name: p.name || '',
  phone: p.phone || '',
  headline: p.headline || '',
  location: p.location || '',
  summary: p.summary || '',
  skills: (p.skills || []).join(', '),
  birth_date: p.birth_date || '',
  national_number: '',
});

const splitSkills = (text) => text.split(/[,\n;،]+/).map((s) => s.trim()).filter(Boolean);

export default function ProfileEditor({ initial }) {
  const router = useRouter();
  const [profile, setProfile] = useState(initial);
  const [form, setForm] = useState(() => toForm(initial));
  const [clearNumber, setClearNumber] = useState(false);
  const [overwrite, setOverwrite] = useState(false);
  const [errors, setErrors] = useState({});
  const [notice, setNotice] = useState({ kind: '', text: '' });
  const [busy, setBusy] = useState('');
  const photoInput = useRef(null);
  const cvInput = useRef(null);

  const say = (kind, text) => setNotice({ kind, text });
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  /** Put CV guesses into the form. Empty fields only, unless "overwrite" is ticked. Nothing is saved yet. */
  function applyAutofill(auto, force = overwrite) {
    if (!auto?.readable) {
      say('warn', 'We could not read text from this CV (it may be a scanned image). Fill the fields by hand.');
      return;
    }
    const fields = auto.fields || {};
    const filled = [];
    const next = { ...form };
    for (const key of ['name', 'phone', 'headline', 'location', 'summary', 'birth_date', 'national_number']) {
      const guess = fields[key];
      if (!guess) continue;
      const has = key === 'national_number' ? profile.has_national_number && !clearNumber : Boolean(form[key]);
      if (!has || force) { next[key] = guess; filled.push(LABELS[key]); }
    }
    if (fields.skills?.length) {
      const existing = splitSkills(form.skills);
      const seen = new Set(existing.map((s) => s.toLowerCase()));
      const added = fields.skills.filter((s) => !seen.has(s.toLowerCase()));
      if (added.length) { next.skills = [...existing, ...added].join(', '); filled.push(LABELS.skills); }
    }
    setForm(next);
    say('ok', filled.length
      ? `Filled in from your CV: ${filled.join(', ')}. Review it, then press Save.`
      : 'Nothing new was found in your CV.');
  }

  async function uploadPhoto(file) {
    if (!file) return;
    if (!/^image\/(jpeg|png|webp)$/.test(file.type)) return say('err', 'Use a JPG, PNG or WebP image.');
    if (file.size > MAX_PHOTO) return say('err', 'The photo must be 3 MB or smaller.');
    setBusy('photo'); say('', '');
    const body = new FormData(); body.append('photo', file);
    const r = await call('/photo', { method: 'POST', body });
    setBusy('');
    if (!r.ok) return r.message && say('err', r.message);
    setProfile(r.data.profile); say('ok', 'Photo updated.'); router.refresh();
  }

  async function removePhoto() {
    setBusy('photo');
    const r = await call('/photo', { method: 'DELETE' });
    setBusy('');
    if (!r.ok) return r.message && say('err', r.message);
    setProfile(r.data.profile); say('ok', 'Photo removed.'); router.refresh();
  }

  async function uploadCv(file) {
    if (!file) return;
    if (!/\.(pdf|docx)$/i.test(file.name)) return say('err', 'Upload your CV as a PDF or DOCX file.');
    if (file.size > MAX_CV) return say('err', 'The CV must be 5 MB or smaller.');
    setBusy('cv'); say('', '');
    const body = new FormData(); body.append('cv', file);
    const r = await call('/cv', { method: 'POST', body });
    setBusy('');
    if (!r.ok) return r.message && say('err', r.message);
    setProfile(r.data.profile); router.refresh();
    applyAutofill(r.data.autofill);
  }

  async function runAutofill() {
    setBusy('autofill'); say('', '');
    const r = await call('/cv/autofill', { method: 'POST' });
    setBusy('');
    if (!r.ok) return r.message && say('err', r.message);
    applyAutofill(r.data.autofill);
  }

  async function removeCv() {
    setBusy('cv');
    const r = await call('/cv', { method: 'DELETE' });
    setBusy('');
    if (!r.ok) return r.message && say('err', r.message);
    setProfile(r.data.profile); say('ok', 'CV removed.'); router.refresh();
  }

  async function save(e) {
    e.preventDefault();
    setBusy('save'); setErrors({}); say('', '');
    const body = {
      name: form.name,
      phone: form.phone,
      headline: form.headline,
      location: form.location,
      summary: form.summary,
      skills: splitSkills(form.skills),
      birth_date: form.birth_date || null,
    };
    if (clearNumber) body.clear_national_number = true;
    else if (form.national_number.trim()) body.national_number = form.national_number;

    const r = await call('', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    setBusy('');
    if (!r.ok) { setErrors(r.errors); return r.message && say('err', r.message); }
    setProfile(r.data.profile);
    setForm(toForm(r.data.profile));
    setClearNumber(false);
    say('ok', 'Profile saved.');
    router.refresh();
  }

  const field = (id, label, props = {}, hint) => (
    <div className="fld">
      <label htmlFor={id}>{label}</label>
      {props.as === 'textarea' ? (
        <textarea id={id} name={id} rows={4} maxLength={2000} value={form[id]} onChange={set(id)} aria-invalid={errors[id] ? 'true' : undefined} />
      ) : (
        <input id={id} name={id} value={form[id]} onChange={set(id)} aria-invalid={errors[id] ? 'true' : undefined} {...props} />
      )}
      {errors[id] ? <p className="err">{errors[id]}</p> : hint ? <p className="hint">{hint}</p> : null}
    </div>
  );

  return (
    <div className="pf-editor">
      <div className={`pf-notice ${notice.kind ? `pf-notice--${notice.kind}` : ''}`} role="status" aria-live="polite">{notice.text}</div>

      <section className="pf-card" aria-labelledby="ed-photo">
        <h2 id="ed-photo">Photo</h2>
        <div className="pf-photo">
          <Avatar profile={profile} size={112} />
          <div className="pf-photo__btns">
            <input ref={photoInput} type="file" accept="image/jpeg,image/png,image/webp" hidden onChange={(e) => { uploadPhoto(e.target.files?.[0]); e.target.value = ''; }} />
            <button type="button" className="btn btn--primary" disabled={busy === 'photo'} onClick={() => photoInput.current?.click()}>
              {busy === 'photo' ? 'Uploading...' : profile.has_photo ? 'Change photo' : 'Upload photo'}
            </button>
            {profile.has_photo && <button type="button" className="btn btn--ghost" disabled={busy === 'photo'} onClick={removePhoto}>Remove</button>}
            <p className="hint">JPG, PNG or WebP, up to 3 MB. It is cropped to a square.</p>
          </div>
        </div>
      </section>

      <section className="pf-card" aria-labelledby="ed-cv">
        <h2 id="ed-cv">CV and auto-fill</h2>
        {profile.has_cv && <p className="pf-cv__name">{profile.cv_name}</p>}
        <input ref={cvInput} type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" hidden onChange={(e) => { uploadCv(e.target.files?.[0]); e.target.value = ''; }} />
        <div className="pf-actions pf-actions--tight">
          <button type="button" className="btn btn--primary" disabled={busy === 'cv'} onClick={() => cvInput.current?.click()}>
            {busy === 'cv' ? 'Uploading...' : profile.has_cv ? 'Replace CV' : 'Upload CV'}
          </button>
          {profile.has_cv && (
            <>
              <button type="button" className="btn btn--ghost" disabled={busy === 'autofill'} onClick={runAutofill}>
                {busy === 'autofill' ? 'Reading...' : 'Auto-fill from CV'}
              </button>
              <a className="btn btn--ghost" href="/profile-api/profile/cv" download>Download</a>
              <button type="button" className="btn btn--ghost" disabled={busy === 'cv'} onClick={removeCv}>Remove</button>
            </>
          )}
        </div>
        <label className="pf-check">
          <input type="checkbox" checked={overwrite} onChange={(e) => setOverwrite(e.target.checked)} />
          Replace fields I already filled in
        </label>
        <p className="hint">PDF or DOCX, up to 5 MB. We read your CV on our server to suggest answers. Nothing is saved until you press Save.</p>
      </section>

      <form className="pf-card pf-form" onSubmit={save} noValidate aria-labelledby="ed-details">
        <h2 id="ed-details">Your details</h2>
        {field('name', 'Full name', { autoComplete: 'name', maxLength: 80, required: true })}
        {field('headline', 'Job title', { maxLength: 120, placeholder: 'e.g. Laravel developer' })}
        {field('phone', 'Phone', { type: 'tel', inputMode: 'tel', autoComplete: 'tel', maxLength: 32, dir: 'ltr' })}
        {field('location', 'Location', { autoComplete: 'address-level2', maxLength: 120, placeholder: 'City, Country' })}
        {field('birth_date', 'Birth date', { type: 'date', autoComplete: 'bday', max: new Date().toISOString().slice(0, 10) })}

        <div className="fld">
          <label htmlFor="national_number">National number</label>
          <input
            id="national_number" name="national_number" inputMode="numeric" autoComplete="off" maxLength={24} dir="ltr"
            value={form.national_number} onChange={set('national_number')} disabled={clearNumber}
            placeholder={profile.has_national_number ? `Saved: ${profile.national_number_masked}. Type to replace.` : '14 digits'}
            aria-invalid={errors.national_number ? 'true' : undefined}
          />
          {errors.national_number ? <p className="err">{errors.national_number}</p> : <p className="hint">Stored encrypted and shown masked. A valid 14-digit number also fills your birth date.</p>}
          {profile.has_national_number && (
            <label className="pf-check">
              <input type="checkbox" checked={clearNumber} onChange={(e) => setClearNumber(e.target.checked)} />
              Remove my saved national number
            </label>
          )}
        </div>

        {field('skills', 'Skills', { maxLength: 800, placeholder: 'PHP, Laravel, SQL' }, 'Separate skills with commas.')}
        {field('summary', 'About you', { as: 'textarea' })}

        <button type="submit" className="auth-submit" disabled={busy === 'save'}>{busy === 'save' ? 'Saving...' : 'Save profile'}</button>
      </form>
    </div>
  );
}
