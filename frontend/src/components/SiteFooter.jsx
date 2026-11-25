import { Github, Globe, Linkedin, Mail } from 'lucide-react'

import { CONTACT } from '../config/contact'
import { BrandMark } from './BrandMark'

const display = (url) => url.replace(/^https?:\/\/(www\.)?/, '').replace(/\/$/, '')

export function SiteFooter({ className = '' }) {
  const links = [
    CONTACT.email && { href: `mailto:${CONTACT.email}`, icon: Mail, label: 'Email', text: CONTACT.email },
    CONTACT.github && { href: CONTACT.github, icon: Github, label: 'GitHub', text: display(CONTACT.github), external: true },
    CONTACT.linkedin && { href: CONTACT.linkedin, icon: Linkedin, label: 'LinkedIn', text: display(CONTACT.linkedin), external: true },
    CONTACT.website && { href: CONTACT.website, icon: Globe, label: 'Website', text: display(CONTACT.website), external: true },
  ].filter(Boolean)

  return (
    <footer className={`site-footer ${className}`.trim()}>
      <div className="site-footer-inner">
        <p className="site-footer-credit">
          <BrandMark size={24} />
          <span>
            <strong>Yes Officer</strong> <span className="site-footer-by">· built by {CONTACT.name}</span>
          </span>
        </p>
        <ul className="site-footer-links" aria-label="Contact">
          {links.map(({ href, icon: Icon, label, text, external }) => (
            <li key={label}>
              <a
                href={href}
                {...(external ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
                aria-label={`${label}: ${text}${external ? ' (opens in a new tab)' : ''}`}
              >
                <Icon size={16} aria-hidden="true" />
                <span>{text}</span>
              </a>
            </li>
          ))}
        </ul>
      </div>
    </footer>
  )
}
