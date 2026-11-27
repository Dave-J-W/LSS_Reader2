#!/usr/bin/env bash
# Watch Dave-J-W/LSS_Reader2's issues and pull requests; one stdout line per event (for the Monitor tool).
#
# Usage:
#   bash .claude/skills/issue-watch/watch.sh <state-dir>                      # everything (main man)
#   bash .claude/skills/issue-watch/watch.sh <state-dir> --label lane:local-data --branch-prefix claude/local-data-
#                                                                             # one lane (the owner's PC)
# --label L          only issues carrying label L (new ones, and new comments on them)
# --branch-prefix P  only pull requests whose branch starts with P (new ones, head moves, new comments,
#                    which is how a reviewer's requests arrive)
# Only `gh` is needed: its built-in --jq stands in for jq, which the owner's Windows PC lacks.
#
# State (kept between runs, so a re-armed watch reports only what is new):
#   counts      issue or pull-request number <TAB> comment count
#   prs         every pull request number seen
#   head_<n>    the head commit of open pull request n
REPO=Dave-J-W/LSS_Reader2
S=${1:?state directory}; shift
LABEL=; PREFIX=
while [ $# -gt 0 ]; do
  case "$1" in
    --label) LABEL=$2; shift 2 ;;
    --branch-prefix) PREFIX=$2; shift 2 ;;
    *) echo "unknown option $1" >&2; exit 2 ;;
  esac
done
mkdir -p "$S"
ISSUES="repos/$REPO/issues?state=all&per_page=100&sort=updated&direction=desc"
[ -n "$LABEL" ] && ISSUES="$ISSUES&labels=$LABEL"

# Pull requests of interest (all of them, or those on PREFIX branches): "number<TAB>branch<TAB>state<TAB>merged<TAB>sha<TAB>title"
prs() {
  gh api "repos/$REPO/pulls?state=all&sort=created&direction=desc&per_page=30" \
    --jq '.[] | "\(.number)\t\(.head.ref)\t\(.state)\t\(.merged_at // "-")\t\(.head.sha[0:7])\t\(.title)"' 2>/dev/null |
    awk -F'\t' -v p="$PREFIX" 'p=="" || index($2,p)==1'
}
# Issues of interest with their comment counts: "number<TAB>comments<TAB>state<TAB>kind<TAB>title".
# Without filters: issues only (pull requests are watched separately). With a prefix: also the comments
# on that lane's pull requests.
issues() {
  { gh api "$ISSUES" --jq '.[] | select(.pull_request|not) | "\(.number)\t\(.comments)\t\(.state)\tissue\t\(.title)"' 2>/dev/null
    if [ -n "$PREFIX" ]; then
      for n in $(prs | cut -f1); do
        gh api "repos/$REPO/issues/$n" --jq '"\(.number)\t\(.comments)\t\(.state)\tpr\t\(.title)"' 2>/dev/null
      done
    fi; }
}
latest() {   # the newest comment of issue or PR $1 with $2 comments: the last page, past 100 comments
  page=$(( ($2 + 99) / 100 )); [ "$page" -ge 1 ] || page=1
  gh api "repos/$REPO/issues/$1/comments?per_page=100&page=$page" --jq '.[-1] | "\(.created_at): \(.body[0:120] | gsub("\n";" "))"' 2>/dev/null || echo "?"
}

[ -f "$S/counts" ] || issues | cut -f1,2 > "$S/counts"
[ -f "$S/prs" ] || prs | cut -f1 > "$S/prs"
touch "$S/counts" "$S/prs"

while true; do
  if issues > "$S/now.tsv" && [ -s "$S/now.tsv" ]; then
    while IFS=$'\t' read -r n c st kind t; do
      old=$(awk -F'\t' -v n="$n" '$1==n{print $2}' "$S/counts")
      if [ -z "$old" ]; then
        [ "$kind" = issue ] && echo "NEW ISSUE #$n ($st, $c comments): $t"
        printf '%s\t%s\n' "$n" "$c" >> "$S/counts"
      elif [ "$old" != "$c" ]; then
        label=ISSUE; [ "$kind" = pr ] && label=PR
        echo "$label #$n comments $old -> $c ($st): $t | latest: $(latest "$n" "$c")"
        awk -F'\t' -v n="$n" -v c="$c" 'BEGIN{OFS="\t"} $1==n{$2=c} {print}' "$S/counts" > "$S/counts.new" && mv "$S/counts.new" "$S/counts"
      fi
    done < "$S/now.tsv"
  fi
  # pull requests opened and merged between two polls never show as open: the newest of every state
  prs > "$S/pr.tsv"
  while IFS=$'\t' read -r n ref st m sha t; do
    [ -n "$n" ] || continue
    [ "$m" = - ] && m=      # "-" stands for "not merged": an empty field would shift the rest (read joins tabs)
    if ! grep -qx "$n" "$S/prs"; then
      echo "$n" >> "$S/prs"
      echo "NEW PR #$n ($ref, $st${m:+, merged $m}): $t"
    fi
    if [ "$st" = open ]; then
      prev=$(cat "$S/head_$n" 2>/dev/null)
      if [ -n "$prev" ] && [ "$prev" != "$sha" ]; then echo "PR #$n head moved $prev -> $sha ($ref)"; fi
      echo "$sha" > "$S/head_$n"
    fi
  done < "$S/pr.tsv"
  [ -n "$WATCH_ONCE" ] && exit 0      # for testing: one poll, then stop
  sleep 60
done
