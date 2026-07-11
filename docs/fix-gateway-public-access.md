# Gateway 公网访问修复指南（腾讯云）

## 诊断结论

- **本机 127.0.0.1:8081** ✅ 通
- **公网 111.229.200.179:8081** ❌ 超时
- **公网 111.229.200.179:22** ✅ 通（实例可达）
- **iptables / ufw / firewalld** 均未拦截 8081

**根因：腾讯云安全组未放行 8081 端口。**

---

## 修复方案（二选一）

### 方案 A：腾讯云控制台手动修改（推荐，2 分钟）

1. 登录 [腾讯云 CVM 控制台](https://console.cloud.tencent.com/cvm)
2. 找到实例 `111.229.200.179`
3. 进入「安全组」→「入站规则」→「添加规则」
4. 填写：
   - 协议端口：`TCP:8081`
   - 来源：`0.0.0.0/0`（或你的办公 IP）
   - 策略：允许
   - 备注：`worker-bee gateway`
5. 保存，等待 10 秒生效

### 方案 B：命令行自动修改（需要 SecretId/SecretKey）

```bash
cd /root/.nanobot/workspace/worker-bee
bash scripts/fix_sg_8081.sh <SecretId> <SecretKey> [Region]
```

示例：
```bash
bash scripts/fix_sg_8081.sh AKIDxxxxx xxxxxxxx ap-guangzhou
```

---

## 验证

修改后执行：
```bash
nc -zv -w 3 111.229.200.179 8081
```

预期输出：`Connection to 111.229.200.179 8081 port succeeded!`

---

## 附：tccli 已安装

```bash
tccli version
```

如需手动查询安全组：
```bash
tccli configure set secretId xxx
tccli configure set secretKey xxx
tccli configure set region ap-guangzhou
tccli cvm DescribeSecurityGroups
```
