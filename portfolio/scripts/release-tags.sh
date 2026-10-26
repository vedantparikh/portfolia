#!/bin/sh
# Tags for the GHCR images published by .github/workflows/release.yml.
#   IMAGE_PREFIX=ghcr.io/vedantparikh release-tags.sh api edge <full-sha>
#   IMAGE_PREFIX=ghcr.io/vedantparikh release-tags.sh web version <full-sha> 0.1.0
set -eu

usage() {
  echo "usage: IMAGE_PREFIX=ghcr.io/<owner> $0 <api|web> <edge|version> <full-sha> [X.Y.Z]" >&2
  exit 2
}

[ $# -ge 3 ] || usage
name=$1
kind=$2
sha=$3
version=${4:-}
prefix=${IMAGE_PREFIX:?set IMAGE_PREFIX to ghcr.io/<owner>}

case "$name" in
  api | web) ;;
  *) usage ;;
esac
printf '%s' "$sha" | grep -Eq '^[0-9a-fA-F]{7,}$' || {
  echo "sha must be hex and at least 7 characters" >&2
  exit 1
}
short=$(printf '%s' "$sha" | cut -c1-7)
base="${prefix}/portfolia-${name}"

case "$kind" in
  edge)
    printf '%s:edge\n%s:sha-%s\n' "$base" "$base" "$short"
    ;;
  version)
    printf '%s' "$version" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$' || {
      echo "version must be X.Y.Z" >&2
      exit 1
    }
    minor=${version%.*}
    printf '%s:%s\n%s:%s\n%s:sha-%s\n' "$base" "$version" "$base" "$minor" "$base" "$short"
    ;;
  *)
    usage
    ;;
esac
