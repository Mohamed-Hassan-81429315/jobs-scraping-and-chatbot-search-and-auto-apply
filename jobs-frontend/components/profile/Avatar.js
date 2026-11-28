import { initials } from '../../lib/profile-format';

/** Photo if the user has one, otherwise their initials. Plain <img>: the file is private and proxied. */
export default function Avatar({ profile, size = 96 }) {
  const style = { width: size, height: size, fontSize: Math.round(size / 2.6) };
  if (profile.has_photo) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        className="pf-avatar"
        style={style}
        src={`/profile-api/profile/photo?v=${profile.photo_version}`}
        alt={`${profile.name}'s photo`}
        width={size}
        height={size}
      />
    );
  }
  return <span className="pf-avatar pf-avatar--initials" style={style} aria-hidden="true">{initials(profile.name)}</span>;
}
