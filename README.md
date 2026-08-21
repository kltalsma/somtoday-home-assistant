# Somtoday voor Home Assistant

Deze custom integration haalt het Somtoday-rooster rechtstreeks op en maakt per leerling een kalender-entiteit aan. Daarnaast verschijnt een sensor met het laatste cijfer. Er wordt elke 15 minuten vernieuwd; de kalender kan voor elke gewenste periode ophalen.

## Installatie via HACS

1. Installeer [HACS](https://hacs.xyz/) als dat nog niet aanwezig is.
2. Open **HACS -> Integraties -> menu met drie puntjes -> Custom repositories**.
3. Voeg deze GitHub-repository toe met categorie **Integration**.
4. Zoek naar **Somtoday**, installeer hem en herstart Home Assistant.
5. Ga naar **Instellingen -> Apparaten en diensten -> Integratie toevoegen -> Somtoday**.
6. Voeg elk kind afzonderlijk toe. De tenant-ID is het UUID-deel in `https://inloggen.somtoday.nl/tenant/<tenant-ID>` nadat je op de Somtoday-inlogpagina de school hebt gekozen.

## Handmatige installatie

1. Kopieer de map `custom_components/somtoday` naar `/config/custom_components/somtoday` op de Home Assistant-server.
2. Herstart Home Assistant.
3. Ga naar **Instellingen -> Apparaten en diensten -> Integratie toevoegen -> Somtoday**.
4. Vul de volledige schoolnaam, gebruikersnaam en het wachtwoord van kind 1 in. Herhaal dit voor kind 2.

Er ontstaan dan onder andere `calendar.<naam>_rooster` en `sensor.<naam>_laatste_cijfer`. Een standaard Calendar card kan beide roosters tegelijk tonen.

## Beperking

De integratie gebruikt Somtoday's niet-officiele, legacy OAuth password grant. Wanneer de school dit blokkeert, of SSO/2FA afdwingt, kan de installatie niet inloggen. In dat geval is de officiële iCalendar-koppeling de betrouwbaardere fallback.
