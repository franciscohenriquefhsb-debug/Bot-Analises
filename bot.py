import os
import math
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TOKEN")
API_KEY = os.getenv("API_KEY") # Key da API-Football pra BR1, PL, etc
HEADERS = {"x-apisports-key": API_KEY}

def calc_over_prob(media_gols):
    def poisson(k, media):
        if media <= 0: return 0
        return (media**k * math.exp(-media)) / math.factorial(k)

    p0 = poisson(0, media_gols)
    p1 = poisson(1, media_gols)
    p2 = poisson(2, media_gols)
    p3 = poisson(3, media_gols)
    p4 = poisson(4, media_gols)

    over_05 = 1 - p0
    over_15 = 1 - (p0 + p1)
    over_25 = 1 - (p0 + p1 + p2)
    over_35 = 1 - (p0 + p1 + p2 + p3)
    over_45 = 1 - (p0 + p1 + p2 + p3 + p4)

    return {
        "o05": over_05 * 100, "u05": p0 * 100,
        "o15": over_15 * 100, "u15": (p0 + p1) * 100,
        "o25": over_25 * 100, "u25": (p0 + p1 + p2) * 100,
        "o35": over_35 * 100, "u35": (p0 + p1 + p2 + p3) * 100,
        "o45": over_45 * 100, "u45": (p0 + p1 + p2 + p3 + p4) * 100,
    }

def get_team_stats(team_id, league_id, season):
    url = "https://v3.football.api-sports.io/teams/statistics"
    params = {"team": team_id, "league": league_id, "season": season}
    r = requests.get(url, headers=HEADERS, params=params, timeout=10)
    data = r.json()["response"]

    goals_for_home = float(data["goals"]["for"]["average"]["home"] or 0)
    goals_for_away = float(data["goals"]["for"]["average"]["away"] or 0)
    goals_against_home = float(data["goals"]["against"]["average"]["home"] or 0)
    goals_against_away = float(data["goals"]["against"]["average"]["away"] or 0)

    return {
        "casa_faz": goals_for_home,
        "casa_sofre": goals_against_home,
        "fora_faz": goals_for_away,
        "fora_sofre": goals_against_away
    }

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "Bot de análise Over/Under\n\n"
    msg += "Comandos:\n"
    msg += "/jogos COPA - Copa do Mundo 2026\n"
    msg += "/jogos BR1 - Brasileirão\n"
    msg += "/jogos PL - Premier League\n"
    msg += "/jogos SA - Serie A Italiana\n"
    msg += "/jogos LL - La Liga\n"
    msg += "/jogos BL1 - Bundesliga\n"
    msg += "/jogos LIBERTA - Libertadores\n"
    msg += "/jogos SULA - Sul-Americana\n"
    msg += "/jogos COPABR - Copa do Brasil"
    await update.message.reply_text(msg)

async def jogos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Use: /jogos COPA, /jogos BR1, /jogos PL...")
        return

    liga_code = context.args[0].upper()
    await update.message.reply_text(f"Buscando jogos da {liga_code}... Aguarde 15s")

    try:
        if liga_code == "COPA":
            # API 1: worldcup26.ir - Grátis pra Copa 2026
            url = "https://worldcup26.ir/get/games"
            r = requests.get(url, timeout=15)
            all_games = r.json()

            # Filtra jogos futuros
            agora = datetime.now().timestamp() * 1000
            fixtures = [g for g in all_games if g['timestamp'] > agora]
            fixtures = sorted(fixtures, key=lambda x: x['timestamp'])[:5]

            if not fixtures:
                await update.message.reply_text("Nenhum jogo futuro da Copa encontrado.")
                return

            msg_final = "📊 ANÁLISES - COPA 2026\n\n"
            jogos_encontrados = 0

            for jogo in fixtures:
                home = jogo['home_team']['name']
                away = jogo['away_team']['name']

                # worldcup26.ir não tem stats por time ainda
                # Usa média histórica das Copas: 2.6 gols
                media_esperada = 2.6
                probs = calc_over_prob(media_esperada)

                jogos_encontrados += 1
                data = datetime.fromtimestamp(jogo['timestamp'] / 1000)
                dia_hora = data.strftime("%d/%m %H:%M")

                msg_final += f"🏆 {home} x {away} - {dia_hora}\n"
                msg_final += f"Média Copa: {media_esperada} gols\n"
                msg_final += f"O2.5: {probs['o25']:.1f}% | U2.5: {probs['u25']:.1f}%\n"
                msg_final += "───────────────\n"

            if jogos_encontrados == 0:
                msg_final += "Nenhum jogo encontrado."

        else:
            # API 2: API-Football pras outras ligas
            ligas = {
                "BR1": 71, "PL": 39, "SA": 135, "LL": 140, "BL1": 78, "L1": 61,
                "LIBERTA": 13, "SULA": 11, "COPABR": 73
            }

            if liga_code not in ligas:
                await update.message.reply_text("Liga inválida. Use: COPA, BR1, PL, SA, LL, BL1, LIBERTA, SULA, COPABR")
                return

            league_id = ligas[liga_code]
            season = datetime.now().year
            hoje = datetime.now().strftime("%Y-%m-%d")
            url = f"https://v3.football.api-sports.io/fixtures?league={league_id}&season={season}&date={hoje}"

            r = requests.get(url, headers=HEADERS, timeout=15)
            fixtures = r.json()["response"]

            if not fixtures:
                await update.message.reply_text(f"Nenhum jogo da {liga_code} hoje.")
                return

            msg_final = f"📊 ANÁLISES - {liga_code}\n\n"
            jogos_encontrados = 0

            for jogo in fixtures[:5]:
                home = jogo["teams"]["home"]
                away = jogo["teams"]["away"]

                try:
                    stats_home = get_team_stats(home["id"], league_id, season)
                    stats_away = get_team_stats(away["id"], league_id, season)

                    media_esperada = (stats_home["casa_faz"] + stats_away["fora_sofre"] + stats_away["fora_faz"] + stats_home["casa_sofre"]) / 2
                    media_esperada = round(media_esperada, 2)

                    probs = calc_over_prob(media_esperada)

                    if probs["o25"] < 75:
                        continue

                    jogos_encontrados += 1
                    data_hora = jogo['fixture']['date']
                    dia = data_hora[8:10] + "/" + data_hora[5:7]
                    hora = data_hora[11:16]

                    msg_final += f"🏆 {home['name']} x {away['name']} - {dia} {hora}\n"
                    msg_final += f"Média esperada: {media_esperada} gols\n"
                    msg_final += f"{home['name']} casa: {stats_home['casa_faz']:.2f} feitos | {stats_home['casa_sofre']:.2f} sofridos\n"
                    msg_final += f"{away['name']} fora: {stats_away['fora_faz']:.2f} feitos | {stats_away['fora_sofre']:.2f} sofridos\n"
                    msg_final += f"O2.5: {probs['o25']:.1f}% ✅ | U2.5: {probs['u25']:.1f}%\n"
                    msg_final += "───────────────\n"

                except Exception:
                    continue

            if jogos_encontrados == 0:
                msg_final += "Nenhum jogo com Over 2.5 acima de 75% hoje."

        await update.message.reply_text(msg_final)

    except Exception as e:
        await update.message.reply_text(f"Erro ao buscar dados: {str(e)}")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("jogos", jogos))
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
