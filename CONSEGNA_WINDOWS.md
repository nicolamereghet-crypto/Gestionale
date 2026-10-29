# Consegna al cliente (Windows)

L'installatore `Gestionale-Setup-X.Y.Z.exe` viene creato da **GitHub Actions** su un
computer Windows virtuale: dal Mac non serve fare niente oltre a `git push`.

## 1. Prima volta: mettere il progetto su GitHub

1. Crea un repository **privato** su github.com (es. `gestionale`), senza README.
2. Nel Terminale, dalla cartella del progetto:

   ```bash
   git init
   git add .
   git commit -m "Versione 1.0.0"
   git branch -M main
   git remote add origin https://github.com/TUO-UTENTE/gestionale.git
   git push -u origin main
   ```

   Il file `.gitignore` esclude database, backup e log: **i dati del cliente non vanno mai su GitHub.**

3. Su GitHub apri la scheda **Actions**: parte "Installatore Windows".
   In circa 5-10 minuti:
   - prova che l'app si avvii su Windows;
   - crea `Gestionale.exe` e l'installatore;
   - lo prova di nuovo.

   Se diventa verde, l'installatore è in fondo alla pagina dell'esecuzione, sotto **Artifacts**.

## 2. Pubblicare una versione per il cliente

1. In `version.py` imposta la versione (es. `1.0.0`).
2. Poi:

   ```bash
   git commit -am "Versione 1.0.0"
   git tag v1.0.0
   git push && git push --tags
   ```

3. A fine build trovi l'installatore in **Releases** sulla pagina del repository. Lo scarichi e lo mandi al cliente (email, WeTransfer, chiavetta).

## 3. Installazione sul PC del cliente

1. Doppio clic su `Gestionale-Setup-1.0.0.exe`. Non servono permessi di amministratore.
2. Windows potrebbe mostrare **"Windows ha protetto il PC"**, perché il programma non ha una firma digitale a pagamento. Clic su **Ulteriori informazioni → Esegui comunque**. Succede solo all'installazione.
3. Al primo avvio il programma chiede se c'è un file con i dati da importare:
   - **Sì** → scegli il `gestionale.db` che il cliente usa oggi (sta nella cartella `data` della vecchia versione);
   - **No** → si parte da vuoto.

## 4. Dove stanno i dati del cliente

| Cosa | Windows | Mac (tuo) |
|---|---|---|
| Database | `%LOCALAPPDATA%\Gestionale\gestionale.db` | `~/Library/Application Support/Gestionale/` |
| Backup automatici (ultimi 30, uno a ogni avvio) | `Documenti\Gestionale - Backup\` | `~/Documents/Gestionale - Backup/` |
| Registro errori | `%LOCALAPPDATA%\Gestionale\gestionale.log` | nella cartella del database |

- Installare una nuova versione o disinstallare **non tocca mai** i dati.
- Se `Documenti` è sincronizzata con OneDrive, i backup finiscono anche nel cloud.
- Per recuperare un backup: chiudi il programma, copia il file di backup al posto di `gestionale.db` e rinominalo `gestionale.db`.

## 5. Aggiornamenti futuri

Modifichi sul Mac, aumenti la versione in `version.py`, fai tag e push (punto 2) e mandi il nuovo installatore.
Il cliente lo esegue sopra la versione vecchia: le fatture restano.

## Se qualcosa va storto

- **Build rossa su GitHub:** apri l'esecuzione e leggi il passaggio fallito.
  "Prova l'app da sorgente" rosso = errore nel codice, che va corretto prima di creare il `.exe`.
- **Errore sul PC del cliente:** compare una finestra con il percorso del file `gestionale.log`. Fattelo mandare.
