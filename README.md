Ja, hier ist ein Entwurf für eine README.md-Datei, die du für dein GitHub-Repository verwenden kannst. Sie erklärt auf einfache und verständliche Weise, was das Skript tut, für wen es nützlich ist und wie man es verwendet.

Clipboard History Tool

Ein einfacher, aber leistungsstarker Manager für die Zwischenablage unter Windows, der den Verlauf aller kopierten Texte speichert und schnell wieder zugänglich macht.

Dieses Tool wurde für alle entwickelt, die häufig Texte, Links oder Code-Schnipsel kopieren und einfügen und dabei den Überblick behalten möchten. Anstatt denselben Text mehrmals kopieren zu müssen, können Sie einfach auf den Verlauf Ihrer Zwischenablage zugreifen.

Funktionen

Verlauf speichern: Speichert automatisch jeden neuen Texteintrag, den Sie in die Zwischenablage kopieren.

Schneller Zugriff: Öffnen Sie das Verlaufsfenster jederzeit mit einem globalen Hotkey (standardmäßig Win + V).

Anpinnen: Wichtige Einträge können angepinnt werden, damit sie immer oben in der Liste bleiben und nicht gelöscht werden.

Suchen: Filtern Sie Ihren Verlauf schnell, um genau das zu finden, was Sie suchen.

Direktes Einfügen: Wählen Sie einen Eintrag aus, und er wird automatisch an der Cursor-Position eingefügt (optional).

Einfache Verwaltung: Löschen Sie einzelne Einträge oder den gesamten Verlauf mit nur einem Klick.

Anpassbares Design:

Wählen Sie zwischen einem hellen, einem dunklen oder dem System-Theme.

Passen Sie die Schriftgröße nach Ihren Wünschen an.

Persistente Speicherung: Ihr Verlauf und Ihre angepinnten Einträge bleiben auch nach einem Neustart des Computers erhalten.

Voraussetzungen

Bevor Sie das Skript ausführen können, stellen Sie sicher, dass Python 3 auf Ihrem System installiert ist.

Installation

Laden Sie den Code herunter: Klonen Sie dieses Repository oder laden Sie es als ZIP-Datei herunter.

Installieren Sie die Abhängigkeiten: Öffnen Sie eine Kommandozeile (CMD oder PowerShell) im Projektordner und führen Sie den folgenden Befehl aus, um alle notwendigen Bibliotheken zu installieren:

code
Bash
download
content_copy
expand_less
pip install PyQt5 pyperclip pynput
Anwendung

Starten Sie die Anwendung: Führen Sie die Python-Datei (.py) per Doppelklick aus oder starten Sie sie über die Kommandozeile:

code
Bash
download
content_copy
expand_less
python <name_der_datei>.py

Im Hintergrund aktiv: Das Programm läuft unauffällig im Hintergrund und überwacht Ihre Zwischenablage.

Fenster öffnen: Drücken Sie die Tastenkombination Win + V (oder den von Ihnen festgelegten Hotkey), um das Verlaufsfenster zu öffnen. Es erscheint in der unteren rechten Ecke Ihres Bildschirms.

Eintrag auswählen:

Klicken Sie auf einen Eintrag in der Liste, um ihn erneut in die Zwischenablage zu kopieren und (falls aktiviert) direkt einzufügen.

Klicken Sie auf das Stecknadel-Symbol (📍), um einen Eintrag anzupinnen (📌).

Klicken Sie auf das Mülleimer-Symbol (🗑️), um einen Eintrag zu löschen.

Fenster schließen: Klicken Sie außerhalb des Fensters oder drücken Sie die Esc-Taste, um es zu schließen.

Einstellungen

Klicken Sie auf die Schaltfläche "Einstellungen", um das Konfigurationsfenster zu öffnen. Hier können Sie folgende Anpassungen vornehmen:

Max. Einträge: Legen Sie fest, wie viele (nicht angepinnte) Einträge im Verlauf maximal gespeichert werden sollen.

Hotkey: Ändern Sie die Tastenkombination zum Öffnen des Fensters.

Theme: Wählen Sie zwischen "Hell", "Dunkel" oder "System" (passt sich automatisch an Ihre Windows-Einstellungen an).

Schriftgröße (pt): Vergrößern oder verkleinern Sie die Schrift in der Anwendung.

Nach Auswahl direkt einfügen: Wenn diese Option aktiviert ist, wird ein ausgewählter Eintrag nicht nur kopiert, sondern auch sofort an der aktuellen Cursor-Position eingefügt (simuliert Strg + V).
