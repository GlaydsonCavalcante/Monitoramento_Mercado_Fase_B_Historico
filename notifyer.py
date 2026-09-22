from datetime import datetime
import os
from typing import Optional
import requests


def enviar_alerta_telegram(
    nome_arquivo: str,
    runner_id: int,
    total_itens: int,
    sucessos: int,
    desistencias: int,
    falhas_acesso: int,
    tempo_execucao_s: float,
) -> None:
  bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
  chat_ids_raw = os.getenv("TELEGRAM_CHAT_ID")

  if not bot_token or not chat_ids_raw:
    return

  chat_ids = [c.strip() for c in chat_ids_raw.split(",") if c.strip()]
  url_msg = f"https://api.telegram.org/bot{bot_token}/sendMessage"

  universo_util = max(1, total_itens - desistencias)
  taxa_eficacia = (sucessos / universo_util) * 100.0
  minutos = int(tempo_execucao_s // 60)
  segundos = int(tempo_execucao_s % 60)

  msg = (
      f"<b>LOTE CONCLUÍDO | RUNNER {runner_id}</b>\n\n"
      f"<b>Arquivo:</b> <code>{nome_arquivo}</code>\n"
      f"<b>Data/Hora:</b> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
      f"<b>Total no Lote:</b> {total_itens}\n"
      f"<b>Textos Extraídos:</b> {sucessos} ({taxa_eficacia:.1f}% viáveis)\n"
      f"<b>Desistências Estruturais:</b> {desistencias}\n"
      f"<b>Falhas de Acesso / Timeout:</b> {falhas_acesso}\n"
      f"<b>Duração:</b> {minutos}m {segundos}s\n"
      f"<b>Status:</b> {'META ATINGIDA (>=42%)' if taxa_eficacia >= 42.0 else 'FINALIZADO'}"
  )

  for chat_id in chat_ids:
    try:
      requests.post(
          url_msg,
          json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"},
          timeout=15,
      )
    except Exception as err:
      print(
          f"Falha ao enviar notificacao Telegram para {chat_id}: {err}",
          flush=True,
      )

def enviar_resumo_runner_telegram(
    runner_id: int,
    total_alocados: int,
    tempo_total_s: float,
    lista_detalhada: list[dict]
) -> None:
    """Envia despacho consolidado com a lista de arquivos avaliados pelo runner."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return

    minutos = int(tempo_total_s // 60)
    segundos = int(tempo_total_s % 60)

    sucessos = sum(1 for a in lista_detalhada if a["status"] == "PROCESSADO")
    saltados = sum(1 for a in lista_detalhada if a["status"] == "SALTADO")
    falhas = sum(1 for a in lista_detalhada if a["status"] == "FALHA")

    linhas_arquivos = []
    for a in lista_detalhada:
        if a["status"] == "PROCESSADO":
            linhas_arquivos.append(f"✅ <code>{a['nome']}</code> ({a['eficacia']:.1f}%)")
        elif a["status"] == "SALTADO":
            linhas_arquivos.append(f"⏭️ <code>{a['nome']}</code> (Saltado: {a['eficacia']:.1f}%)")
        else:
            linhas_arquivos.append(f"❌ <code>{a['nome']}</code> (Falha)")

    bloco_itens = "\n".join(linhas_arquivos)
    
    texto = (
        f"🏁 <b>[Runner {runner_id}] Conclusão do Bloco</b>\n"
        f"Tempo Total: {minutos}m {segundos}s | Arquivos: {total_alocados}\n\n"
        f"<b>Resumo:</b>\n"
        f"• Processados: {sucessos}\n"
        f"• Saltados: {saltados}\n"
        f"• Falhas: {falhas}\n\n"
        f"<b>Detalhamento:</b>\n"
        f"{bloco_itens}"
    )

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": texto, "parse_mode": "HTML"}
    
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logging.error(f"Erro ao enviar resumo do runner {runner_id}: {e}")
