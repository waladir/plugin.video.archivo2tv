<h1>Sledování O2TV</h1>
<p>
Kodi doplňek Sledování O2TV umožňuje sledovaní O2TV.
<p>
<a href="https://www.xbmc-kodi.cz/prispevek-zpetne-sledovani-o2tv-ott">Vlákno na fóru XBMC-Kodi.cz</a><br><br>
Inspirovaný addonem pro zpětné sledování ze SledovaniTV od @Saros  jsem se snažil udělat něco podobného pro OTT O2TV. Doplněk umožnuje zpětné přehrávání pořadů a základní práci s nahrávkami.

Po instalaci doplňku je potřeba v nastavení zadat přihlašovací údaje (stejné jako na webu www.o2tv.cz), do Device Id libovolnou změť alfanumerických znaků, Device Name a Device Type budou předvyplněné.<br><br>

v2.1.4 (2020-12-19)<br>
- kontrola EPG DB při startu Kodi<br>
- odflitrování nestandardtních kategorií, které způsobují pády (Vánoce)<br>
- upravené ukládání historie vyhledávání (by Listener)<br><br>

v2.1.3 (2020-12-13)<br>
- úprava položek v nastavení<br>
- přidání možnosti stahovat nekomprimovanou EPG DB (řeší možné problémy s rozbalením na některých Androidech)<br><br>

v2.1.2 (2020-12-06)<br>
- omezení zamykání DB EPG<br>
- doplněné logování průběhu synchronizace dat (debug)<br>
- nenačítání kódu pro stahovaní pokud je vypnuté v nastavení<br>
- ošetření spouštění živého vysílání v IPTV Simple Clientovi bez EPG<br><br>

v2.1.1 (2020-11-29)<br>
- použití kešovaných EPG dat (lze vypnout v nastavení)<br><br>

v2.1.0 (2020-11-23)<br>
- vypnutí dotahování chybějících detailů k pořadům<br>
- zobrazeni loga kanalu, pokud detailní informace chybí<br>
- přidání závislosti na verzi pythonu (oddělení větví pro Matrix a Leia a starší)<br><br>

v2.0.9 (2020-11-04)<br>
- parsování datumu z IPTV Simple Clienta (velké díky listenerovi)<br><br>

v2.0.8 (2020-10-18)<br>
- úprava titulku při přehrávání přes playlist z IPTVSC<br>
- omezení kontextového menu jen pro PVR EPG<br><br>

v2.0.7 (2020-10-10)<br>
- filtrování kanálů bez streamu<br>
- přidané mazání položek v historii vyhledávání do kontextového menu<br>
- oprava problémů v Kodi 19 (Matrix)<br><br>

v2.0.6 (2020-10-04)<br>
- oprava zobrazení nahrávek při chybějícím EPG<br>
- přejmenování vypnutí informačních hlášek v nastavení<br><br>

v2.0.5 (2020-10-04)<br>
- oprava vypnutí zobrazování informačních hlášek o práci s EPG (stahování/generování)<br>
- přejmenování v nastavení<br><br>

v2.0.4 (2020-09-30)<br>
- ošetření redirectu streamu na https, pokud O2 vrátí URL s http protokolem<br><br>

v2.0.3 (2020-09-27)<br>
- přidání kontroly session před začátkem stahování EPG<br>
- přidání informačních hlášek o průběhu stahování EPG<br>
- přidání možnosti vypnout v nastavení informační hlášky z procesů běžících na pozadí (generování EPG pro IPTV Simple Clienta, stahování EPG)<br>
- posun začátku stahování EPG z 30 na 60 s po startu Kodi<br>
- snížení pauz v cyklu plánovače<br>
- přidané stažení EPG dat před generováním EPG v nastavení<br>
- možnost v nastavení vypnout procesy běžící na pozadí (stahování EPG z O2, stahování streamů, generování EPG pri IPTV Simple Clienta)<br>
- oprava spouštění v historii kanálů IPTV Simple Clienta<br>
- oprava přehrávání živého vysílání bez EPG dat<br><br>

v2.0.2 (2020-09-20)<br>
- oprava přehrávání kanálů pro dospělé<br>
- ošetření chyb při stahování EPG<br>
- při generování EPG v nastavení se nebude spouštět stahování EPG z O2<br>
- přidané detailní logování průběhu stahování EPG do kodi.log (se zapnutým debugem)<br><br>

v2.0.1 (2020-09-05)<br>
- aktualizace změn v EPG při změnách na straně O2<br>
- doplnění položek Související pořady a Vysílání pořadu do kontextového menu ve výsledcích vyhledávání<br><br>

v2.0.0 (2020-08-31)<br>
- skrytí položky stahování v kontextovém menu, pokud není povolené v nastavení<br>
- oprava nefunkčního přehrávání ve výsledcích vyhledávání<br>
- kompatibilita s Kodi 19 (Python 3)<br><br>
 
v1.9.1 (2020-08-23)<br>
- úprava třídění podle abecedy v kategoriích<br>
- při vyhledání stejných pořadů se nezobrazují budoucí pořady<br>
- podpora stahování pořadů<br><br>

v1.9.0 (2020-08-15)<br>
- ukládání kategorií O2 s aktualizací jednou za 24 hodin<br>
- využití EPG DB k plánování nahrávek a získání informací o pořadech při přehrávání streamu<br>
- odstranění zbývajících přímých volání API O2 (mimo nahrávek, vyhledávání a URL streamu)<br>
- odstraněna možnost použití EPG DB v nastavení, bude se používat vždy mimo vyhledávání a kategorie<br>
- zmenšená prodleva při ukončení Kodi/doplňku<br>
- u live, archivních pořadů a pořadů v kategoriích přidáno do kontextového menu vyhledání souvisejících a stejných pořadů<br>
- opravena chyba v nahrávkách, pokud žádná neexistovala<br><br>

v1.8.6 (2020-08-09)<br>
- oprava plnění DB<br><br>

v1.8.5 (2020-08-08)<br>
- z nastavení jsou odstraněné volby pro zobrazení detailů a posteru k pořadům, budou se zobrazovat vždy a pořetnů pro generování EPG, které bude vždy 8/8<br>
- interní rozšíření škály ratingu z 0-10 na 0-100, v EPG pak rozšíření na jedno desetinné číslo.<br>
- do EPG DB přidané informace o seriálech (sezóna, episoda), doplněné i do generování EPG pro IPTV Simple Clienta<br>
- upravená údržba EPG DB - mažou se data u pořadů, které nejsou k dispozici, tj. starší než 7 dnů, mimo dat k nahrávkám<br><br>

v1.8.4 (2020-08-02)<br>
- oprava chyby při přehrávání v kategoriích<br><br>

v1.8.3 (2020-07-30)<br>
- oprava chyby při přehrávání živého vysílání v IPTV Simple Clientovi<br><br>

v1.8.2 (2020-07-29)<br>
- oprava přehrávání Fishing and Hunting v IPTV Simple Clientovi<br>
- vypnutí kešovaní nabídek v archivu<br>
- v archivu se zobrazují všechny pořady, které lze přehrát<br>
- doplnění alternativního popisu a posteru, pokud nejsou dostupné standardní<br>
- přechod na interní EPG u nahrávek a u načítání seznamů u archivu a živého vysílání<br>
- opravena chyba, kdy při povoleném přidávání nových kanálů docházelo k přidání všech kanálů. Dojde i k opravení dat.<br>
- ošetření kanálů, které jsou v seznamu kanálů, ale chybí k nim detailní informace<br>
- omezení počtu dnů při generování EPG pro IPTV Simple Clienta na 8 dnů zpátky<br><br>

v1.8.1 (2020-07-27)<br>
- předělaná práce s kanály, lokální ukládání dat o kanálech, aktualizace jednou za 24 hodin<br>
- možnost v ruční editaci přidat (položka menu) nebo odstranit (kontextové menu) kanál<br>
- přidáno varování s možností změny nastavení pokud při ruční editaci nebo načtení seznamu z O2 je zapnuté automatické přidávání kanálu<br>
- přepsání generování EPG pro IPTV Simple Clienta<br>
- přidání lokální databáze EPG, s automatickou aktualizací dat<br>
- načítání detailů u pořadech z EPG DB<br>
- možnost vypnutí použití EPG DB v nastavení (defaultně zapnuto)<br>
- přidána možnost použít v playlistu pro IPTV Simple Clienta čísla kanálů z doplňku<br><br>

v1.7.2 (2020-07-19)<br>
- přidané uložení O2 session s platností jeden den a automatickou aktualizací<br>
- přidaná možnost manuálního vygenrování nové O2 session v nastavení<br>
- ve vyhledávání se nově zobrazují ve výsledcích jen pořady z aktuálního seznamu kanálů<br>
- přidané zobrazení pořadů z archivu podle kategorií<br><br>

v1.7.1 (2020-07-10)<br>
- přidaná možnost v nastavení vypnout spouštění pořadu přepnutím na kanál v EPG IPTV Simple Clienta (funguje pak přepínaní během přehrávání pořadu)<br>
- oprava chyby, kdy v archivu chyběly pořady, které začínaly před půlnocí a končily až druhý den<br>
- doplněné ikony k položkám hlavního menu<br>
- počet dní zobrazovaných pro archiv nebo pro nastavení nahrávek a maximální počty dní pro generování EPG byly rozšířené z původních 7 na 10 dnů<br>
- optimalizovaná funkce na dotahování detailních informacím o pořadu a jejich rozšíření o rok a zemi vzniku, originální název, žánry a ID v IMDB<br>
- rozšířené data v EPG o obsazení a režiséry, zemi a rok vzniku, žánry a hodnocení<br>
- oprava chyby při mazání nahrávek<br>
- doplnění odkazu na fórum do informací o doplňku<br><br>

v1.7.0 (2020-07-05)<br>
- přidaná podpora přetáčení u živých pořadů s MPEG-DASH/MPEG-DASH-web (lze vypnout v nastavení)<br>
- přidané zobrazení polohy v nabídkách (musí podporovat použité téma)<br>
- rozdělení kódu do modulů<br>
- oprava drobných chyb<br>
- přehrávání pořadu v EPG IPTV Simple Clienta při Přepnout na kanál (funguje i u pořadů z archivu)<br>
- pokud v IPTV Simple Clientovi chybí EPG, spustí se live stream (končilo chybou)<br>
- oprava generování playlistu pro omezenou skupinu kanálů<br>
- v nastavení přidaná možnost vybrat jinou O2 službu než první<br>
- nahrazení speciálních znaků v EPG za html entity, odstraňuje problém s importem EPG IPTV Simple Clientem<br><br>

v1.6.3 (2020-06-27)<br>
- opraveno přehrávání aktuálně běžícího pořadu z IPTV Simple Clienta s nastaveným MPEG-DASH-web streamem<br><br>

v1.6.2 (2020-06-27)<br>
- opravena defaultní barva popisku u živého vysílání<br>
- přidání informací o hercích a režisérech<br>
- stránkování kanálů u živého vysílání<br>
- úprava vracení streamu pro IPTV Simple Clienta, aby se aktualizovaly nedávno sledované kanály<br><br>

v1.6.1 (2020-06-21)<br>
- přidáno nastavení barvy popisku u živého vysílání<br><br>

v1.6.0 (2020-06-14)<br>
- přidání kontextového menu do PVR klienta umožnujující přehrávání a nastavení nahrávek u O2 (vyžaduje shodné pojmenování kanálů, ideálně použít EPG Z doplňku)<br>
- do EPG doplňeno stahování detailních informací o pořadech, pokud jsou k dispozici <br><br>
  
v1.5.3 (2020-06-11)<br>
- přidané generování EPG v XMLTV pro IPTV Simple Clienta<br>   
- generování EPG je možné pouštět automaticky při startu Kodi a následně v nastavitelném intervalu<br><br>

v1.5.2 (2020-06-09)<br>
- oddělení nastavení streamu do samostatné záložky<br>
- možnost nastavit dotaz z výběrem HD/SD při spuštění streamu (funguje u HLS streamu a nesmí být zaškrtlé Pouze SD)<br>
- opravené spouštění živého vysílání z IPTV Simple Clienta + přidání informací o pořadu včetně loga<br>
- úprava barvy titulku u živého vysílání<br><br>

v1.5.1 (2020-06-07)<br>
- aktualizace seznamu živého vysílání po ukončení přehrávání (pokud není zapnutné načítání detailů)<br> 
- optimalizace kódu<br><br>

v1.5.0 (2020-06-04)<br>
- upravené jméno doplňku u chybových hlášek<br>
- přidaná možnost v nastavení měnit typ streamu mezi HLS, a adaptivní MPEG-DASH (až 1080p) a MPEG-DASH-web (až 720p). MPEG-DASH vyžaduje nainstalovaný InputStream Adaptive, v kterém lze nastavit i podmínky pro výběr streamu.<br>
- přepracované menu, u plánování nahrávek je výběr po dnech se zobrazením detailů<br>
- u živého vysílání je možné zapnout dotažení detailních informací v nastavení (trvá delší dobu)<br><br>

v1.4.5 (2020-05-31)<br>
- úprava zobrazení aktuálního pořadí u kanálů<br>
- upravené zdvojování kanálů při načtení uživatelského seznamu<br><br>

v1.4.4 (2020-05-25)<br>
- oprava načítání uživatelského seznamu kanálů, pokud obsahuje diakritiku<br>
- doplněné mapování ID kanálů z uživatelského seznamu na jméno kanálu<br>
- přidaný aktuální pořad do nabídky kanálů<br><br>

v1.4.3 (2020-05-23)<br>
- možnost v nastavení zakázat automatické přidávání kanálů, které nejsou v současném seznamu kanálů<br><br>

v1.4.2 (2020-05-20)<br>
- u datumů se zobrazuje den v týdnu<br> 
- oprava načítání uživatelského seznamu kanálů, pokud obsahuje diakritiku<br>
- upravený titulek u položek ve vyhledání (sjednoceno s nahrávkami)<br>
- opravené zobrazení popisu u nahrávek<br><br>

v1.4.1 (2020-05-18)<br>
- přidání mazání a plánování nahrávek do kontextového menu (c)<br>
- zobrazení budoucího programu pro nastavení nahrávek (zobrazení detailů je možné samostatně zapnout v nastavení, načtení seznamu je ale výrazně pomalejší)<br>
- opravy chyb v nahrávkách<br><br> 

v1.4.0 (2020-05-16)<br>
- přejmenování addonu<br>
- generovaní device id, pokud není vyplněné<br>
- možnost skrýt položku Pořadí kanálů v menu<br>
- možnost načíst uživatelský seznam kanálů z O2, resetnout celý seznam, oprava chyby v pořadí kanálů<br>
- upravený formát titulku pořadu<br>
- přidáno přehrávání nahrávek<br>
- generování playlistu a streamu pro IPTV Simple Clienta<br><br>

v1.3.1 (2020-05-15)<br>
- oprava seznamu kanálů u více balíčků<br>
- nastavení historie<br><br>

v1.3.0 (2020-05-15)<br>
- přechod na jiné API O2<br>
- zrušení závislosti na InputStream Adaptive<br>
- volba SD/HD kvality v nastavení<br>
- možnost nastavení pokračování pořadu i po jeho skončení podle EPG<br>
- možnost vypnutí zobrazení detailních informace, log a posterů<br>
- doplnění informací k live streamu<br>
- historie vyhledávání<br>
- nastavení pořadí programů<br><br>

v1.2.3 (2020-05-11)<br>
- přidání do XBMC-Kodi CZ/SK repozitáře<br><br>

v1.2.0 (2020-05-10)<br>
- přidáno vyhledávání<br>
- zobrazení ratingu<br>
- jméno pořadu u živého streamu<br>
- ošetření chybného přihlášení<br><br>

v1.1.0 (2020-05-10)<br>
- přidáno živé vysílání<br><br>

v1.0.2 (2020-05-09)<br>
- přidaná kontrola nastavení, opravené filtrování kanálů podle balíčku O2TV<br><br>

v1.0.1 (2020-05-09)<br>
- upravené závislosti a opravená možná chyba s kódováním<br><br>

v1.0.0 (2020-05-07)<br><br>
- první vydání<br>
</p>
