import type {ReactNode} from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import Heading from '@theme/Heading';
import styles from './styles.module.css';

type FeatureItem = {
  title: string;
  emoji: string;
  description: ReactNode;
  to: string;
};

const FeatureList: FeatureItem[] = [
  {
    title: 'Ubuntu',
    emoji: '🐧',
    to: '/docs/ubuntu/install',
    description: (
      <>
        One command installs it: <code>curl ... | bash</code>. Apt handles
        every dependency. Runs as a tray app with a popup for incoming
        calls, and best-effort Bluetooth call audio.
      </>
    ),
  },
  {
    title: 'macOS',
    emoji: '🍎',
    to: '/docs/macos/install',
    description: (
      <>
        A native SwiftUI menu bar app with the same incoming-call popup
        and answer/decline/hang-up controls as Ubuntu, built from
        source.
      </>
    ),
  },
  {
    title: 'Android',
    emoji: '📱',
    to: '/docs/android/install',
    description: (
      <>
        One APK works with either desktop client — just point it at your
        computer's IP address. Download it straight from GitHub
        Releases.
      </>
    ),
  },
];

function Feature({title, emoji, description, to}: FeatureItem) {
  return (
    <div className={clsx('col col--4')}>
      <Link to={to} className={styles.featureCard}>
        <div className="text--center">
          <span className={styles.featureEmoji} role="img" aria-hidden="true">
            {emoji}
          </span>
        </div>
        <div className="text--center padding-horiz--md">
          <Heading as="h3">{title}</Heading>
          <p>{description}</p>
        </div>
      </Link>
    </div>
  );
}

export default function HomepageFeatures(): ReactNode {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
