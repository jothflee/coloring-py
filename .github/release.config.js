// release.config.js
module.exports = {
  branches: ['main'],
  repositoryUrl: `https://github.com/${process.env.GITHUB_REPOSITORY_OWNER}/${process.env.GITHUB_REPOSITORY_NAME}`,
  plugins: [
    [
        '@semantic-release/commit-analyzer',
        {
          preset: 'conventionalcommits',
          releaseRules: [
            { type: 'chore', release: 'patch' },
            { type: 'feat', release: 'minor' },
            { type: 'fix', release: 'patch' },
            { type: 'perf', release: 'patch' },
            { scope: 'no-release', release: false },
          ],
        },
      ],
    '@semantic-release/release-notes-generator',
    '@semantic-release/changelog',
    '@semantic-release/github',
    '@semantic-release/git',
    '@semantic-release/docker',
  ],
  docker: {
    image: `ghcr.io/${process.env.GITHUB_REPOSITORY_OWNER}/${process.env.GITHUB_REPOSITORY_NAME}`,
    registry: 'ghcr.io',
    tag: 'latest',
  },
  git: {
    assets: ['CHANGELOG.md', 'package.json', 'package-lock.json'],
    message: 'chore(release): ${nextRelease.version} [skip ci]\n\n${nextRelease.notes}',
  },
};