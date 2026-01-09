import os
import json
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters
)
import gspread
from datetime import datetime
import re

# =========================
# CONFIGURAÇÕES
# =========================

TELEGRAM_TOKEN = "7987750191:AAH8IbvbvySpIyijPBS9lejpMX9kZ8Qcew0"

PLANILHA_NOME = "FINANÇAS TESTE"
CAMINHO_CREDENCIAIS = "credentials.json"

LIMITE_MENSAL = 3000  # ajuste como quiser

# =========================
# GOOGLE SHEETS
# =========================

if "GOOGLE_CREDENTIALS" in os.environ:
    creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
    gc = gspread.service_account_from_dict(creds_dict)
else:
    gc = gspread.service_account(filename=CAMINHO_CREDENCIAIS)
sheet = gc.open(PLANILHA_NOME).sheet1

# =========================
# FUNÇÃO DE REGISTRO
# =========================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        texto = update.message.text.lower().strip()
        usuario = update.message.from_user.first_name

        match = re.search(r"([a-zA-Zçãõéíóú]+)\D+([\d,.]+)", texto)

        if not match:
            await update.message.reply_text(
                "❌ Formato inválido.\n"
                "Use: categoria valor\n"
                "Ex: mercado 120"
            )
            return

        categoria = match.group(1)
        valor = float(match.group(2).replace(",", "."))

        agora = datetime.now()
        data = agora.strftime("%d/%m/%Y")
        mes = agora.strftime("%m/%Y")

        sheet.append_row([data, mes, categoria, valor, usuario])

        await update.message.reply_text(
            f"✅ Gasto registrado!\n"
            f"📅 {data}\n"
            f"📂 {categoria}\n"
            f"💰 R$ {valor:.2f}\n"
            f"👤 {usuario}"
        )

        # ===== ALERTA DE LIMITE =====
        registros = sheet.get_all_records()
        total_mes = sum(
            r["Valor"] for r in registros if r["Mês"] == mes
        )

        if total_mes > LIMITE_MENSAL:
            await update.message.reply_text(
                f"⚠️ Limite mensal ultrapassado!\n"
                f"💸 Total do mês: R$ {total_mes:.2f}"
            )

    except Exception as e:
        await update.message.reply_text("❌ Erro ao registrar o gasto.")
        print("ERRO:", e)

# =========================
# COMANDO /resumo
# =========================

async def resumo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    agora = datetime.now()
    mes_atual = agora.strftime("%m/%Y")

    registros = sheet.get_all_records()

    total = 0
    por_pessoa = {}
    por_categoria = {}

    for r in registros:
        if r["Mês"] == mes_atual:
            valor = r["Valor"]
            total += valor

            pessoa = r["Usuário"]
            por_pessoa[pessoa] = por_pessoa.get(pessoa, 0) + valor

            categoria = r["Categoria"]
            por_categoria[categoria] = por_categoria.get(categoria, 0) + valor

    texto = f"📊 Resumo de {mes_atual}\n\n"
    texto += f"💰 Total do mês: R$ {total:.2f}\n\n"

    texto += "👩‍❤️‍👨 Por pessoa:\n"
    for p, v in por_pessoa.items():
        texto += f"• {p}: R$ {v:.2f}\n"

    texto += "\n📂 Por categoria:\n"
    for c, v in por_categoria.items():
        texto += f"• {c}: R$ {v:.2f}\n"

    await update.message.reply_text(texto)

# =========================
# INICIALIZAÇÃO
# =========================

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("resumo", resumo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Bot financeiro de casal rodando...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

