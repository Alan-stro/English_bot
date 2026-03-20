import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import date


QQ_SMTP_HOST = "smtp.qq.com"
QQ_SMTP_PORT = 465


def send_daily_email(topic: str, analyses: list[dict]):
    """
    发送每日英语学习邮件：
    - 正文：摘要 + 句型 + 语法（HTML 可读）
    - 附件：每个视频一个 .txt 墨墨导入文件
    """
    msg = MIMEMultipart("mixed")
    msg["Subject"] = f"每日英语 | {topic} | {date.today()}"
    msg["From"]    = os.environ["QQ_MAIL_USER"]
    msg["To"]      = os.environ["TO_EMAIL"]

    # ── 正文 HTML ──
    html = _build_html(topic, analyses)
    msg.attach(MIMEText(html, "html", "utf-8"))

    # ── 附件：每个视频一个墨墨 txt ──
    for i, a in enumerate(analyses, 1):
        if not a.get("cards"):
            continue
        attachment = _build_attachment(a, i)
        msg.attach(attachment)

    # ── 发送 ──
    try:
        with smtplib.SMTP_SSL(QQ_SMTP_HOST, QQ_SMTP_PORT) as server:
            server.login(
                os.environ["QQ_MAIL_USER"],
                os.environ["QQ_MAIL_PASSWORD"],  # QQ 授权码，不是登录密码
            )
            server.send_message(msg)
        print("[邮件] 发送成功")
    except Exception as e:
        print(f"[邮件] 发送失败：{e}")
        raise


def _build_attachment(a: dict, index: int) -> MIMEBase:
    """生成墨墨格式 txt 附件"""
    filename = f"markji_{date.today()}_video{index}.txt"
    content  = a["cards"].encode("utf-8")

    part = MIMEBase("application", "octet-stream")
    part.set_payload(content)
    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition",
        f'attachment; filename="{filename}"'
    )
    return part


def _build_html(topic: str, analyses: list[dict]) -> str:
    cards_html = ""
    for i, a in enumerate(analyses, 1):
        thumb = f"https://img.youtube.com/vi/{a['video_id']}/hqdefault.jpg"

        # 句型
        sentences_rows = "".join(
            f"""<tr>
                  <td style="padding:8px 12px;border-bottom:1px solid #f0f0f0;
                             color:#222;line-height:1.7;">{r[0] if len(r)>0 else ''}</td>
                  <td style="padding:8px 12px;border-bottom:1px solid #f0f0f0;
                             color:#666;line-height:1.7;">{r[1] if len(r)>1 else ''}</td>
                </tr>"""
            for r in a.get("sentences", [])
        )

        # 语法
        grammar_rows = "".join(
            f"""<tr>
                  <td style="padding:8px 12px;border-bottom:1px solid #f0f0f0;
                             color:#222;font-weight:500;">{r[0] if len(r)>0 else ''}</td>
                  <td style="padding:8px 12px;border-bottom:1px solid #f0f0f0;
                             color:#555;">{r[1] if len(r)>1 else ''}</td>
                  <td style="padding:8px 12px;border-bottom:1px solid #f0f0f0;
                             color:#888;font-style:italic;">{r[2] if len(r)>2 else ''}</td>
                </tr>"""
            for r in a.get("grammar", [])
        )

        cards_html += f"""
        <div style="margin-bottom:48px;border:1px solid #e8e8e8;
                    border-radius:12px;overflow:hidden;">

          <!-- 视频头部 -->
          <div style="background:#f7f7f7;padding:16px 20px;
                      border-bottom:1px solid #e8e8e8;">
            <div style="color:#999;font-size:12px;margin-bottom:4px;">视频 {i}</div>
            <a href="{a['url']}"
               style="color:#1a73e8;text-decoration:none;
                      font-size:16px;font-weight:500;line-height:1.4;">
              {a['title']}
            </a>
          </div>

          <!-- 缩略图 -->
          <a href="{a['url']}">
            <img src="{thumb}"
                 style="width:100%;display:block;max-height:240px;object-fit:cover;"
                 alt="thumbnail"/>
          </a>

          <div style="padding:24px;">

            <!-- 摘要 -->
            <div style="margin-bottom:28px;">
              <div style="font-size:13px;font-weight:600;color:#1a73e8;
                          letter-spacing:.5px;margin-bottom:10px;">
                视频摘要
              </div>
              <p style="margin:0;color:#333;line-height:1.9;font-size:14px;">
                {a.get('summary','').replace(chr(10),'<br>')}
              </p>
            </div>

            <!-- 实用句型 -->
            <div style="margin-bottom:28px;">
              <div style="font-size:13px;font-weight:600;color:#34a853;
                          letter-spacing:.5px;margin-bottom:10px;">
                实用句型
              </div>
              <table style="width:100%;border-collapse:collapse;font-size:13px;">
                <thead>
                  <tr style="background:#f0faf3;">
                    <th style="padding:8px 12px;text-align:left;color:#34a853;
                               font-weight:600;width:55%;">原句</th>
                    <th style="padding:8px 12px;text-align:left;color:#34a853;
                               font-weight:600;">中文解释</th>
                  </tr>
                </thead>
                <tbody>{sentences_rows}</tbody>
              </table>
            </div>

            <!-- 语法亮点 -->
            <div style="margin-bottom:20px;">
              <div style="font-size:13px;font-weight:600;color:#ea4335;
                          letter-spacing:.5px;margin-bottom:10px;">
                语法亮点
              </div>
              <table style="width:100%;border-collapse:collapse;font-size:13px;">
                <thead>
                  <tr style="background:#fff5f5;">
                    <th style="padding:8px 12px;text-align:left;color:#ea4335;
                               font-weight:600;width:22%;">语法点</th>
                    <th style="padding:8px 12px;text-align:left;color:#ea4335;
                               font-weight:600;width:38%;">解释</th>
                    <th style="padding:8px 12px;text-align:left;color:#ea4335;
                               font-weight:600;">视频例子</th>
                  </tr>
                </thead>
                <tbody>{grammar_rows}</tbody>
              </table>
            </div>

            <!-- 墨墨提示 -->
            <div style="margin-top:20px;padding:12px 16px;
                        background:#fffbea;border-radius:8px;
                        border-left:3px solid #fbbc04;
                        font-size:12px;color:#7a6300;">
              词汇卡片已作为附件随邮件发送（markji_{date.today()}_video{i}.txt），
              可直接导入墨墨记忆卡。
            </div>

          </div>
        </div>
        """

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="font-family:-apple-system,'Helvetica Neue',Arial,sans-serif;
             max-width:680px;margin:0 auto;padding:20px;background:#fafafa;">

  <div style="text-align:center;padding:28px 0 36px;">
    <h1 style="font-size:20px;color:#111;margin:0;font-weight:600;">
      每日英语学习
    </h1>
    <p style="color:#888;margin:8px 0 0;font-size:13px;">
      今日话题：<strong style="color:#333;">{topic}</strong>
      &nbsp;·&nbsp; {date.today()}
    </p>
  </div>

  {cards_html}

  <p style="text-align:center;color:#ccc;font-size:11px;margin-top:40px;">
    由 GitHub Actions + Gemini 自动生成
  </p>
</body>
</html>"""
