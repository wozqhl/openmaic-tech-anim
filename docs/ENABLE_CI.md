# 启用 GitHub Actions CI

当前登录 token 若缺少 `workflow` scope，无法直接推送 `.github/workflows/*`。

## 一次性授权（推荐）

```bash
# 交互登录并勾选 workflow 权限
gh auth login -h github.com -s repo,workflow,read:org

cd ~/openmaic-tech-anim
mkdir -p .github/workflows
cp docs/github-actions-ci.yml .github/workflows/ci.yml
git add .github/workflows/ci.yml
git commit -m "Enable GitHub Actions CI"
git push origin main
```

## 或使用 Fine-grained / classic PAT

Classic PAT 勾选：`repo` + `workflow`，然后：

```bash
export GH_TOKEN=ghp_xxx
git push origin main
```
