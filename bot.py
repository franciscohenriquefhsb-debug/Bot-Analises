async def jogos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Use: /jogos BR1, /jogos PL, /jogos SA, /jogos LL, /jogos COPA, /jogos LIBERTA")
        return

    liga_code = context.args[0].upper()
    ligas = {
        "BR1": 71, "PL": 39, "SA": 135, "LL": 140, "BL1": 78, "L1": 61,
        "COPA": 1, "LIBERTA": 13, "SULA": 11, "COPABR": 73
    }

    if liga_code not in ligas:
        await update.message.reply_text("Liga inválida. Use: BR1, PL, SA, LL, BL1, COPA, LIBERTA, SULA, COPABR")
        return

    league_id = ligas[liga_code]
    season = 2026 if liga_code == "COPA" else datetime.now().year # Força 2026 pra Copa

    # Se for COPA, busca próximos 7 dias. Se não, só hoje.
    if liga_code == "COPA":
        from datetime import timedelta
        hoje = datetime.now()
        data_fim = hoje + timedelta(days=7)
        date_filter = f"from={hoje.strftime('%Y-%m-%d')}&to={data_fim.strftime('%Y-%m-%d')}"
        await update.message.reply_text(f"Buscando jogos da {liga_code} nos próximos 7 dias...")
    else:
        hoje = datetime.now().strftime("%Y-%m-%d")
        date_filter = f"date={hoje}"
        await update.message.reply_text(f"Buscando jogos da {liga_code}... Aguarde 15s")

    try:
        url = f"https://v3.football.api-sports.io/fixtures?league={league_id}&season={season}&{date_filter}"
        r = requests.get(url, headers=HEADERS, timeout=15)
        fixtures = r.json()["response"]

        if not fixtures:
            await update.message.reply_text(f"Nenhum jogo da {liga_code} encontrado no período.")
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
            msg_final += "Nenhum jogo com Over 2.5 acima de 75% no período."

        await update.message.reply_text(msg_final)

    except Exception as e:
        await update.message.reply_text(f"Erro ao buscar dados. Confere se API_KEY está certa no Railway.")

