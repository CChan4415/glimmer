"""Debug script: verify second-degree endpoint returns expected data for a user.

Usage:
    1. Ensure uvicorn is running (so mock SMS works)
    2. Run: cd server && .venv/bin/python scripts/debug_second_degree.py
"""

import json
import subprocess
import sys
import time

import urllib.request

BASE = "http://localhost:8000/v1"
PHONE = "+8613800888001"  # 小明


def req(method, path, token=None, body=None):
    url = f"{BASE}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body else None
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def main():
    print("=" * 60)
    print(f"调试 2 度接口（用户 {PHONE}）")
    print("=" * 60)

    # Step 1: send code
    s, _ = req("POST", "/auth/send-code", body={"phone": PHONE})
    print(f"1. send-code: {s}")
    if s != 200:
        print("   发送失败，可能被限频。等待 60 秒后重跑。")
        return

    # Step 2: need verification code from server log. Ask user to type it.
    code = input("2. 从 uvicorn 日志读到的验证码是? > ").strip()
    s, body = req("POST", "/auth/verify", body={"phone": PHONE, "code": code})
    if s != 200:
        print(f"   登录失败: {body}")
        return
    token = body["data"]["access_token"]
    print(f"   登录成功, token: {token[:25]}...")

    # Step 3: get contacts
    s, body = req("GET", "/me/contacts", token=token)
    print(f"3. 联系人列表: {s}")
    contacts = body["data"]
    for c in contacts:
        matched = c.get("matched_user")
        print(f"   - {c['name']} (group={c['group']}, is_registered={matched is not None})")

    # Step 4: expand 张三's second degree
    zhang = [c for c in contacts if c["name"] == "张三"]
    if not zhang:
        print("   ⚠️ 未找到'张三'，检查种子数据")
        return
    zid = zhang[0]["id"]
    print(f"   展开张三 ({zid}) 的 2 度...")
    s, body = req("GET", f"/me/network/second-degree/{zid}", token=token)
    print(f"4. 2 度接口: {s}")
    if s == 200:
        data = body["data"]
        print(f"   返回 {len(data)} 个 2 度节点:")
        for n in data:
            print(f"   - {n}")
    else:
        print(f"   ⚠️ 响应: {body}")
        print("   ⚠️ 白屏原因可能在此：接口返回异常，前端渲染时崩了")


if __name__ == "__main__":
    main()
