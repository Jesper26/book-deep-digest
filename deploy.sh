#!/usr/bin/env bash
# book-deep-digest 一键部署到 GitHub Pages
# 用法: ./deploy.sh <github用户名> <PAT>
#   PAT 需具备 repo 权限（classic token 勾 repo；或 fine-grained 勾 Contents+Pages 写）
set -euo pipefail

USER="${1:-}"
TOKEN="${2:-}"
REPO="book-deep-digest"

if [ -z "$USER" ] || [ -z "$TOKEN" ]; then
  echo "用法: ./deploy.sh <github用户名> <PAT(需 repo 权限)>" >&2
  exit 1
fi

API="https://api.github.com"
AUTH="Authorization: Bearer $TOKEN"
ACC="Accept: application/vnd.github+json"
VER="X-GitHub-Api-Version: 2022-11-28"

echo ">>> [1/4] 创建仓库 $REPO (public) ..."
curl -s -o /dev/null -w "      HTTP %{http_code}\n" -X POST \
  -H "$AUTH" -H "$ACC" -H "$VER" \
  "$API/user/repos" \
  -d "{\"name\":\"$REPO\",\"description\":\"全书内容自动总结技能 + 精读回顾书库 (GitHub Pages)\",\"homepage\":\"https://$USER.github.io/$REPO/\",\"public\":true,\"auto_init\":false}" || true

echo ">>> [2/4] 配置 remote 并推送 main ..."
git remote remove origin 2>/dev/null || true
git remote add origin "https://$USER:$TOKEN@github.com/$USER/$REPO.git"
git branch -M main
git push -u origin main

echo ">>> [3/4] 开启 GitHub Pages (main 分支 /docs) ..."
# 仓库需已有内容，已在 [2/4] 推送；此步可能需重试一次
for i in 1 2 3; do
  code=$(curl -s -o /tmp/pages_resp.json -w "%{http_code}" -X POST \
    -H "$AUTH" -H "$ACC" -H "$VER" \
    "$API/repos/$USER/$REPO/pages" \
    -d "{\"source\":{\"branch\":\"main\",\"path\":\"/docs\"}}")
  echo "      尝试 $i -> HTTP $code"
  if [ "$code" = "201" ] || [ "$code" = "409" ]; then break; fi
  sleep 3
done

echo ">>> [4/4] 完成"
echo "      站点: https://$USER.github.io/$REPO/"
echo "      仓库: https://github.com/$USER/$REPO"
echo "      提示: Pages 首次构建需 1-2 分钟，若暂时 404 请稍后刷新；"
echo "            可在仓库 Settings > Pages 确认源为 main 分支 /docs 目录。"
