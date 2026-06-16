import os
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TOKEN") or "8812760614:AAG_h8AuUKxRgGWNiMIXv8t2ifYJl9Ws3-s""
API_KEY = os.getenv("API_KEY") or "COLE_SUA_KEY_DA_API_FOOTBALL_AQUI"
HEADERS = {"x-apisports-key": API_KEY}

def calc_over_prob(media_gols):
    # Modelo Poisson simples pra estimar %
    import math
    def poisson(k, media):
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
    r = requests.get(url, headers=HEADERS, params=params)
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
    await update.message.reply_text("Bot de análise online. Use /jogos BR1 pra Brasileirão, /jogos PL pra Premier League")

async def jogos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Use: /jogos BR1, /jogos PL, /jogos SA, /jogos LL")
        return
    
    liga_code = context.args[0].upper()
    ligas = {"BR1": 71, "PL": 39, "SA": 135, "LL": 140} # Brasileirão, Premier, Serie A, La Liga
    
    if liga_code not in ligas:
        await update.message.reply_text("Liga inválida. Use: BR1, PL, SA, LL")
        return
    
    league_id = ligas[liga_code]
    season = datetime.now().year
    hoje = datetime.now().strftime("%Y-%m-%d")
    
    await update.message.reply_text(f"Buscando jogos de hoje... Aguarde 10s")
    
    # Pega jogos do dia
    url = "https://v3.football.api-sports.io/fixtures"
    params = {"date": hoje, "league": league_id, "season": season}
    r = requests.get(url, headers=HEADERS, params=params)
    fixtures = r.json()["response"]
    
    if not fixtures:
        await update.message.reply_text("Nenhum jogo hoje nessa liga.")
        return
    
    msg_final = f"📊 ANÁLISES {hoje} - {liga_code}\n\n"
    
    for jogo in fixtures[:5]: # Limita 5 jogos por causa da API grátis
        home = jogo["teams"]["home"]
        away = jogo["teams"]["away"]
        
        try:
            stats_home = get_team_stats(home["id"], league_id, season)
            stats_away = get_team_stats(away["id"], league_id, season)
            
            # Média de gols esperada: gols que time casa faz em casa + gols que visitante sofre fora
            media_esperada = (stats_home["casa_faz"] + stats_away["fora_sofre"]) / 2 + (stats_away["fora_faz"] + stats_home["casa_sofre"]) / 2
            media_esperada = round(media_esperada, 2)
            
            probs = calc_over_prob(media_esperada)
            
            # Só mostra se Over 2.5 > 75%
            if probs["o25"] < 75:
                continue
                
            msg_final += f"⚽ {home['name']} x {away['name']}\n"
            msg_final += f"Média esperada: {media_esperada} gols\n"
            msg_final += f"Casa: faz {stats_home['casa_faz']:.2f} | sofre {stats_home['casa_sofre']:.2f}\n"
            msg_final += f"Fora: faz {stats_away['fora_faz']:.2f} | sofre {stats_away['fora_sofre']:.2f}\n"
            msg_final += f"Over 0.5: {probs['o05']:.1f}% | Under: {probs['u05']:.1f}%\n"
            msg_final += f"Over 1.5: {probs['o15']:.1f}% | Under: {probs['u15']:.1f}%\n"
            msg_final += f"Over 2.5: {probs['o25']:.1f}% ✅ | Under: {probs['u25']:.1f}%\n"
            msg_final += f"Over 3.5: {probs['o35']:.1f}% | Under: {probs['u35']:.1f}%\n"
            msg_final += f"Over 4.5: {probs['o45']:.1f}% | Under: {probs['u45']:.1f}%\n"
            msg_final += "───────────────\n"
            
        except Exception as e:
            continue
    
    if msg_final == f"📊 ANÁLISES {hoje} - {liga_code}\n\n":
        msg_final += "Nenhum jogo com Over 2.5 acima de 75% hoje."
    
    await update.message.reply_text(msg_final)

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("jogos", jogos))
    app.run_polling()

if __name__ == "__main__":
    main()
