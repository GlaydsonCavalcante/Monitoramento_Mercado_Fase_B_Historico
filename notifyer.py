"""Módulo de mensageria e auditoria via Telegram para esteiras distribuídas."""

from datetime import datetime
import html
import logging
import os
from typing import Any, Dict, List
import requests


def obter_lista_chat_ids(raw_chat_ids: str | None) -> List[str]:
    """Extrai e higieniza lista de IDs de chat a partir de string separada por vírgulas."""
    if not raw_chat_ids:
        return []
    return [c.strip() for c in raw_chat_ids.split(",") if c.strip()]


def enviar_alerta_telegram(
    nome_arquivo: str,
    runner_id: int,
    total_itens: int,
    sucessos: int,
    desistencias: int,
    falhas_acesso: int,
    tempo_execucao_s: float,
) -> None:
    """Envia alerta individual após a conclusão do processamento de um arquivo JSON."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_ids = obter_lista_chat_ids(os.getenv("TELEGRAM_CHAT_ID"))

    if not bot_token or not chat_ids:
        return

    universo_util = max(1, total_itens - desistencias)
    taxa_eficacia = (sucessos / universo_util) * 100.0
    minutos = int(tempo_execucao_s // 60)
    segundos = int(tempo_execucao_s % 60)

    status_meta = "META ATINGIDA (>=42%)" if taxa_eficacia >= 42.0 else "FINALIZADO"

    msg = (
        f"<b>LOTE CONCLUÍDO | RUNNER {runner_id}</b>\n\n"
        f"<b>Arquivo:</b> <code>{html.escape(nome_arquivo)}</code>\n"
        f"<b>Data/Hora:</b> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
        f"<b>Total no Lote:</b> {total_itens}\n"
        f"<b>Textos Extraídos:</b> {sucessos} ({taxa_eficacia:.1f}% viáveis)\n"
        f"<b>Desistências Estruturais:</b> {desistencias}\n"
        f"<b>Falhas de Acesso / Timeout:</b> {falhas_acesso}\n"
        f"<b>Duração:</b> {minutos}m {segundos}s\n"
        f"<b>Status:</b> {status_meta}"
    )

    url_msg = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    for chat_id in chat_ids:
        try:
            requests.post(
                url_msg,
                json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"},
                timeout=15,
            )
        except Exception as err:
            logging.warning(
                f"Falha ao enviar notificação Telegram para {chat_id}: {err}"
            )


def enviar_resumo_runner_telegram(
    runner_id: int,
    total_alocados: int,
    tempo_total_s: float,
    lista_detalhada: List[Dict[str, Any]],
) -> None:
    """Envia relatório consolidado de fechamento da partição de arquivos de um runner."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_ids = obter_lista_chat_ids(os.getenv("TELEGRAM_CHAT_ID"))

    if not bot_token or not chat_ids:
        return

    minutos = int(tempo_total_s // 60)
    segundos = int(tempo_total_s % 60)

    sucessos = sum(1 for a in lista_detalhada if a.get("status") == "PROCESSADO")
    saltados = sum(1 for a in lista_detalhada if a.get("status") == "SALTADO")
    falhas = sum(1 for a in lista_detalhada if a.get("status") == "FALHA")

    linhas_arquivos = []
    for a in lista_detalhada:
        nome = html.escape(str(a.get("nome", "")))
        eficacia = float(a.get("eficacia", 0.0))
        st = a.get("status")
        if st == "PROCESSADO":
            linhas_arquivos.append(f"• <code>{nome}</code> ({eficacia:.1f}%)")
        elif st == "SALTADO":
            linhas_arquivos.append(f"• [SALTADO] <code>{nome}</code> ({eficacia:.1f}%)")
        else:
            linhas_arquivos.append(f"• [FALHA] <code>{nome}</code>")

    detalhamento = "\n".join(linhas_arquivos[:40])

    msg = (
        f"<b>RUNNER {runner_id} | CONCLUSAO DO BLOCO</b>\n"
        f"<b>Duração Total:</b> {minutos}m {segundos}s | <b>Arquivos Alocados:</b> {total_alocados}\n\n"
        f"<b>Consolidação:</b>\n"
        f"• Processados nesta rodada: {sucessos}\n"
        f"• Saltados (já na meta): {saltados}\n"
        f"• Falhas: {falhas}\n\n"
        f"<b>Detalhamento:</b>\n"
        f"{detalhamento}"
    )

    url_msg = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    for chat_id in chat_ids:
        try:
            requests.post(
                url_msg,
                json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"},
                timeout=15,
            )
        except Exception as err:
            logging.warning(
                f"Falha ao enviar resumo do runner {runner_id} para {chat_id}: {err}"
            )
