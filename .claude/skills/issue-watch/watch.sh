#!/usr/bin/env bash
# Watch Dave-J-W/LSS_Reader2's issues and open pull requests; one stdout line per event (for the Monitor tool).
# Usage: bash .claude/skills/issue-watch/watch.sh <state-dir>
# State (kept between runs, so a re-armed watch reports only what is new):
#   counts      issue number <TAB> comment count
#   prs         every pull request number seen
#   head_<n>    the head commit of open pull request n
REPO=Dave-J-W/LSS_Reader2
S=${1:?state directory}
mkdir -p "$S"
[ -f "$S/counts" ] || gh api "repos/$REPO/issues?state=all&per_page=100" --jq '.[] | select(.pull_request|not) | "\(.number)\t\(.comments)"' > "$S/counts" 2>/dev/null || touch "$S/counts"
[ -f "$S/prs" ] || gh api "repos/$REPO/pulls?state=all&per_page=100" --jq '.[].number' > "$S/prs" 2>/dev/null || touch "$S/prs"
while true; do
  if gh api "repos/$REPO/issues?state=all&per_page=100" > "$S/now.json" 2>/dev/null; then
    jq -r '.[] | select(.pull_request|not) | "\(.number)\t\(.comments)\t\(.state)\t\(.title)"' "$S/now.json" > "$S/now.tsv"
    while IFS=$'\t' read -r n c st t; do
      old=$(awk -F'\t' -v n="$n" '$1==n{print $2}' "$S/counts")
      if [ -z "$old" ]; then
        echo "NEW ISSUE #$n ($st, $c comments): $t"
      elif [ "$old" != "$c" ]; then
        page=$(( (c + 99) / 100 )); [ "$page" -ge 1 ] || page=1      # the last page: past 100 comments, page 1 is stale
        last=$(gh api "repos/$REPO/issues/$n/comments?per_page=100&page=$page" --jq '.[-1] | "\(.created_at): \(.body[0:120] | gsub("\n";" "))"' 2>/dev/null || echo "?")
        echo "ISSUE #$n comments $old -> $c ($st): $t | latest: $last"
      fi
    done < "$S/now.tsv"
    cut -f1,2 "$S/now.tsv" > "$S/counts.new" && [ -s "$S/counts.new" ] && mv "$S/counts.new" "$S/counts"
  fi
  # pull requests opened and merged between two polls never show as open: list the newest of every state too
  if gh api "repos/$REPO/pulls?state=all&sort=created&direction=desc&per_page=20" > "$S/pr_all.json" 2>/dev/null; then
    jq -r '.[] | "\(.number)\t\(.head.ref)\t\(.state)\t\(.merged_at // "")\t\(.title)"' "$S/pr_all.json" | while IFS=$'\t' read -r n ref st m t; do
      if ! grep -qx "$n" "$S/prs"; then
        echo "$n" >> "$S/prs"
        echo "NEW PR #$n ($ref, $st${m:+, merged $m}): $t"
      fi
    done
  fi
  if gh api "repos/$REPO/pulls?state=open&per_page=100" > "$S/pr.json" 2>/dev/null; then
    jq -r '.[] | "\(.number)\t\(.head.ref)\t\(.head.sha[0:7])\t\(.title)"' "$S/pr.json" | while IFS=$'\t' read -r n ref sha t; do
      if ! grep -qx "$n" "$S/prs"; then
        echo "$n" >> "$S/prs"
        echo "NEW PR #$n ($ref): $t"
      fi
      prev=$(cat "$S/head_$n" 2>/dev/null)
      if [ -n "$prev" ] && [ "$prev" != "$sha" ]; then echo "PR #$n head moved $prev -> $sha ($ref)"; fi
      echo "$sha" > "$S/head_$n"
    done
  fi
  sleep 60
done
