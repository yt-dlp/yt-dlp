# coding: utf-8
from __future__ import unicode_literals

import functools
import re

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    format_field,
    int_or_none,
    parse_resolution,
    str_or_none,
    try_get,
    unified_timestamp,
    url_or_none,
    urljoin,
    OnDemandPagedList,
)


class PeerTubeIE(InfoExtractor):
    _INSTANCES_RE = r'''(?:
                            # Taken from https://instances.joinpeertube.org/instances
                            40two\.tube|
                            a\.metube\.ch|
                            advtv\.ml|
                            algorithmic\.tv|
                            alimulama\.com|
                            arcana\.fun|
                            archive\.vidicon\.org|
                            artefac-paris\.tv|
                            auf1\.eu|
                            battlepenguin\.video|
                            beertube\.epgn\.ch|
                            befree\.nohost\.me|
                            bideoak\.argia\.eus|
                            birkeundnymphe\.de|
                            bitcointv\.com|
                            cattube\.org|
                            clap\.nerv-project\.eu|
                            climatejustice\.video|
                            comf\.tube|
                            conspiracydistillery\.com|
                            darkvapor\.nohost\.me|
                            daschauher\.aksel\.rocks|
                            digitalcourage\.video|
                            dreiecksnebel\.alex-detsch\.de|
                            eduvid\.org|
                            evangelisch\.video|
                            exo\.tube|
                            fair\.tube|
                            fediverse\.tv|
                            film\.k-prod\.fr|
                            flim\.txmn\.tk|
                            fotogramas\.politicaconciencia\.org|
                            ftsi\.ru|
                            gary\.vger\.cloud|
                            graeber\.video|
                            greatview\.video|
                            grypstube\.uni-greifswald\.de|
                            highvoltage\.tv|
                            hpstube\.fr|
                            htp\.live|
                            hyperreal\.tube|
                            juggling\.digital|
                            kino\.kompot\.si|
                            kino\.schuerz\.at|
                            kinowolnosc\.pl|
                            kirche\.peertube-host\.de|
                            kodcast\.com|
                            kolektiva\.media|
                            kraut\.zone|
                            kumi\.tube|
                            lastbreach\.tv|
                            lepetitmayennais\.fr\.nf|
                            lexx\.impa\.me|
                            libertynode\.tv|
                            libra\.syntazia\.org|
                            libremedia\.video|
                            live\.libratoi\.org|
                            live\.nanao\.moe|
                            live\.toobnix\.org|
                            livegram\.net|
                            lolitube\.freedomchan\.moe|
                            lucarne\.balsamine\.be|
                            maindreieck-tv\.de|
                            mani\.tube|
                            manicphase\.me|
                            media\.gzevd\.de|
                            media\.inno3\.cricket|
                            media\.kaitaia\.life|
                            media\.krashboyz\.org|
                            media\.over-world\.org|
                            media\.skewed\.de|
                            media\.undeadnetwork\.de|
                            medias\.pingbase\.net|
                            melsungen\.peertube-host\.de|
                            mirametube\.fr|
                            mojotube\.net|
                            monplaisirtube\.ddns\.net|
                            mountaintown\.video|
                            my\.bunny\.cafe|
                            myfreetube\.de|
                            mytube\.kn-cloud\.de|
                            mytube\.madzel\.de|
                            myworkoutarenapeertube\.cf|
                            nanawel-peertube\.dyndns\.org|
                            nastub\.cz|
                            offenes\.tv|
                            orgdup\.media|
                            ovaltube\.codinglab\.ch|
                            p2ptv\.ru|
                            p\.eertu\.be|
                            p\.lu|
                            peer\.azurs\.fr|
                            peertube1\.zeteo\.me|
                            peertube\.020\.pl|
                            peertube\.0x5e\.eu|
                            peertube\.alpharius\.io|
                            peertube\.am-networks\.fr|
                            peertube\.anduin\.net|
                            peertube\.anzui\.dev|
                            peertube\.arbleizez\.bzh|
                            peertube\.art3mis\.de|
                            peertube\.atilla\.org|
                            peertube\.atsuchan\.page|
                            peertube\.aukfood\.net|
                            peertube\.aventer\.biz|
                            peertube\.b38\.rural-it\.org|
                            peertube\.beeldengeluid\.nl|
                            peertube\.be|
                            peertube\.bgzashtita\.es|
                            peertube\.bitsandlinux\.com|
                            peertube\.biz|
                            peertube\.boba\.best|
                            peertube\.br0\.fr|
                            peertube\.bridaahost\.ynh\.fr|
                            peertube\.bubbletea\.dev|
                            peertube\.bubuit\.net|
                            peertube\.cabaal\.net|
                            peertube\.cats-home\.net|
                            peertube\.chemnitz\.freifunk\.net|
                            peertube\.chevro\.fr|
                            peertube\.chrisspiegl\.com|
                            peertube\.chtisurel\.net|
                            peertube\.cipherbliss\.com|
                            peertube\.cloud\.sans\.pub|
                            peertube\.cpge-brizeux\.fr|
                            peertube\.ctseuro\.com|
                            peertube\.cuatrolibertades\.org|
                            peertube\.cybercirujas\.club|
                            peertube\.cythin\.com|
                            peertube\.davigge\.com|
                            peertube\.dc\.pini\.fr|
                            peertube\.debian\.social|
                            peertube\.demonix\.fr|
                            peertube\.designersethiques\.org|
                            peertube\.desmu\.fr|
                            peertube\.devloprog\.org|
                            peertube\.devol\.it|
                            peertube\.dtmf\.ca|
                            peertube\.ecologie\.bzh|
                            peertube\.eu\.org|
                            peertube\.european-pirates\.eu|
                            peertube\.euskarabildua\.eus|
                            peertube\.fenarinarsa\.com|
                            peertube\.fomin\.site|
                            peertube\.forsud\.be|
                            peertube\.francoispelletier\.org|
                            peertube\.freenet\.ru|
                            peertube\.freetalklive\.com|
                            peertube\.functional\.cafe|
                            peertube\.gardeludwig\.fr|
                            peertube\.gargantia\.fr|
                            peertube\.gcfamily\.fr|
                            peertube\.genma\.fr|
                            peertube\.get-racing\.de|
                            peertube\.gidikroon\.eu|
                            peertube\.gruezishop\.ch|
                            peertube\.habets\.house|
                            peertube\.hackerfraternity\.org|
                            peertube\.ichigo\.everydayimshuflin\.com|
                            peertube\.ignifi\.me|
                            peertube\.inapurna\.org|
                            peertube\.informaction\.info|
                            peertube\.interhop\.org|
                            peertube\.iselfhost\.com|
                            peertube\.it|
                            peertube\.jensdiemer\.de|
                            peertube\.joffreyverd\.fr|
                            peertube\.kalua\.im|
                            peertube\.kathryl\.fr|
                            peertube\.keazilla\.net|
                            peertube\.klaewyss\.fr|
                            peertube\.kodcast\.com|
                            peertube\.kx\.studio|
                            peertube\.lagvoid\.com|
                            peertube\.lavallee\.tech|
                            peertube\.le5emeaxe\.fr|
                            peertube\.lestutosdeprocessus\.fr|
                            peertube\.librenet\.co\.za|
                            peertube\.logilab\.fr|
                            peertube\.louisematic\.site|
                            peertube\.luckow\.org|
                            peertube\.luga\.at|
                            peertube\.lyceeconnecte\.fr|
                            peertube\.manalejandro\.com|
                            peertube\.marud\.fr|
                            peertube\.mattone\.net|
                            peertube\.maxweiss\.io|
                            peertube\.monlycee\.net|
                            peertube\.mxinfo\.fr|
                            peertube\.myrasp\.eu|
                            peertube\.nebelcloud\.de|
                            peertube\.netzbegruenung\.de|
                            peertube\.newsocial\.tech|
                            peertube\.nicolastissot\.fr|
                            peertube\.nz|
                            peertube\.offerman\.com|
                            peertube\.opencloud\.lu|
                            peertube\.orthus\.link|
                            peertube\.patapouf\.xyz|
                            peertube\.pi2\.dev|
                            peertube\.plataformess\.org|
                            peertube\.pl|
                            peertube\.portaesgnos\.org|
                            peertube\.r2\.enst\.fr|
                            peertube\.r5c3\.fr|
                            peertube\.radres\.xyz|
                            peertube\.red|
                            peertube\.robonomics\.network|
                            peertube\.rtnkv\.cloud|
                            peertube\.runfox\.tk|
                            peertube\.satoshishop\.de|
                            peertube\.scic-tetris\.org|
                            peertube\.securitymadein\.lu|
                            peertube\.semweb\.pro|
                            peertube\.social\.my-wan\.de|
                            peertube\.soykaf\.org|
                            peertube\.stefofficiel\.me|
                            peertube\.stream|
                            peertube\.su|
                            peertube\.swrs\.net|
                            peertube\.takeko\.cyou|
                            peertube\.tangentfox\.com|
                            peertube\.taxinachtegel\.de|
                            peertube\.thenewoil\.xyz|
                            peertube\.ti-fr\.com|
                            peertube\.tiennot\.net|
                            peertube\.troback\.com|
                            peertube\.tspu\.edu\.ru|
                            peertube\.tux\.ovh|
                            peertube\.tv|
                            peertube\.tweb\.tv|
                            peertube\.ucy\.de|
                            peertube\.underworld\.fr|
                            peertube\.us\.to|
                            peertube\.ventresmous\.fr|
                            peertube\.vlaki\.cz|
                            peertube\.w\.utnw\.de|
                            peertube\.westring\.digital|
                            peertube\.xwiki\.com|
                            peertube\.zoz-serv\.org|
                            peervideo\.ru|
                            periscope\.numenaute\.org|
                            perron-tube\.de|
                            petitlutinartube\.fr|
                            phijkchu\.com|
                            pierre\.tube|
                            piraten\.space|
                            play\.rosano\.ca|
                            player\.ojamajo\.moe|
                            plextube\.nl|
                            pocketnetpeertube1\.nohost\.me|
                            pocketnetpeertube3\.nohost\.me|
                            pocketnetpeertube4\.nohost\.me|
                            pocketnetpeertube5\.nohost\.me|
                            pocketnetpeertube6\.nohost\.me|
                            pt\.24-7\.ro|
                            pt\.apathy\.top|
                            pt\.diaspodon\.fr|
                            pt\.fedi\.tech|
                            pt\.maciej\.website|
                            ptb\.lunarviews\.net|
                            ptmir1\.inter21\.net|
                            ptmir2\.inter21\.net|
                            ptmir3\.inter21\.net|
                            ptmir4\.inter21\.net|
                            ptmir5\.inter21\.net|
                            ptube\.horsentiers\.fr|
                            ptube\.xmanifesto\.club|
                            queermotion\.org|
                            re-wizja\.re-medium\.com|
                            regarder\.sans\.pub|
                            ruraletv\.ovh|
                            s1\.gegenstimme\.tv|
                            s2\.veezee\.tube|
                            sdmtube\.fr|
                            sender-fm\.veezee\.tube|
                            serv1\.wiki-tube\.de|
                            serv3\.wiki-tube\.de|
                            sickstream\.net|
                            sleepy\.tube|
                            sovran\.video|
                            spectra\.video|
                            stream\.elven\.pw|
                            stream\.k-prod\.fr|
                            stream\.shahab\.nohost\.me|
                            streamsource\.video|
                            studios\.racer159\.com|
                            testtube\.florimond\.eu|
                            tgi\.hosted\.spacebear\.ee|
                            thaitube\.in\.th|
                            the\.jokertv\.eu|
                            theater\.ethernia\.net|
                            thecool\.tube|
                            tilvids\.com|
                            toob\.bub\.org|
                            tpaw\.video|
                            truetube\.media|
                            tuba\.lhub\.pl|
                            tube-aix-marseille\.beta\.education\.fr|
                            tube-amiens\.beta\.education\.fr|
                            tube-besancon\.beta\.education\.fr|
                            tube-bordeaux\.beta\.education\.fr|
                            tube-clermont-ferrand\.beta\.education\.fr|
                            tube-corse\.beta\.education\.fr|
                            tube-creteil\.beta\.education\.fr|
                            tube-dijon\.beta\.education\.fr|
                            tube-education\.beta\.education\.fr|
                            tube-grenoble\.beta\.education\.fr|
                            tube-lille\.beta\.education\.fr|
                            tube-limoges\.beta\.education\.fr|
                            tube-montpellier\.beta\.education\.fr|
                            tube-nancy\.beta\.education\.fr|
                            tube-nantes\.beta\.education\.fr|
                            tube-nice\.beta\.education\.fr|
                            tube-normandie\.beta\.education\.fr|
                            tube-orleans-tours\.beta\.education\.fr|
                            tube-outremer\.beta\.education\.fr|
                            tube-paris\.beta\.education\.fr|
                            tube-poitiers\.beta\.education\.fr|
                            tube-reims\.beta\.education\.fr|
                            tube-rennes\.beta\.education\.fr|
                            tube-strasbourg\.beta\.education\.fr|
                            tube-toulouse\.beta\.education\.fr|
                            tube-versailles\.beta\.education\.fr|
                            tube1\.it\.tuwien\.ac\.at|
                            tube\.abolivier\.bzh|
                            tube\.ac-amiens\.fr|
                            tube\.aerztefueraufklaerung\.de|
                            tube\.alexx\.ml|
                            tube\.amic37\.fr|
                            tube\.anufrij\.de|
                            tube\.apolut\.net|
                            tube\.arkhalabs\.io|
                            tube\.arthack\.nz|
                            tube\.as211696\.net|
                            tube\.avensio\.de|
                            tube\.azbyka\.ru|
                            tube\.azkware\.net|
                            tube\.bachaner\.fr|
                            tube\.bmesh\.org|
                            tube\.borked\.host|
                            tube\.bstly\.de|
                            tube\.chaoszone\.tv|
                            tube\.chatelet\.ovh|
                            tube\.cloud-libre\.eu|
                            tube\.cms\.garden|
                            tube\.cowfee\.moe|
                            tube\.cryptography\.dog|
                            tube\.darknight-coffee\.org|
                            tube\.dev\.lhub\.pl|
                            tube\.distrilab\.fr|
                            tube\.dsocialize\.net|
                            tube\.ebin\.club|
                            tube\.fdn\.fr|
                            tube\.florimond\.eu|
                            tube\.foxarmy\.ml|
                            tube\.foxden\.party|
                            tube\.frischesicht\.de|
                            tube\.futuretic\.fr|
                            tube\.gnous\.eu|
                            tube\.grap\.coop|
                            tube\.graz\.social|
                            tube\.grin\.hu|
                            tube\.hackerscop\.org|
                            tube\.hordearii\.fr|
                            tube\.jeena\.net|
                            tube\.kai-stuht\.com|
                            tube\.kockatoo\.org|
                            tube\.kotur\.org|
                            tube\.lacaveatonton\.ovh|
                            tube\.linkse\.media|
                            tube\.lokad\.com|
                            tube\.lucie-philou\.com|
                            tube\.melonbread\.xyz|
                            tube\.mfraters\.net|
                            tube\.motuhake\.xyz|
                            tube\.mrbesen\.de|
                            tube\.nah\.re|
                            tube\.nchoco\.net|
                            tube\.novg\.net|
                            tube\.nox-rhea\.org|
                            tube\.nuagelibre\.fr|
                            tube\.nx12\.net|
                            tube\.octaplex\.net|
                            tube\.odat\.xyz|
                            tube\.oisux\.org|
                            tube\.opportunis\.me|
                            tube\.org\.il|
                            tube\.ortion\.xyz|
                            tube\.others\.social|
                            tube\.picasoft\.net|
                            tube\.plomlompom\.com|
                            tube\.pmj\.rocks|
                            tube\.portes-imaginaire\.org|
                            tube\.pyngu\.com|
                            tube\.rebellion\.global|
                            tube\.rhythms-of-resistance\.org|
                            tube\.rita\.moe|
                            tube\.rsi\.cnr\.it|
                            tube\.s1gm4\.eu|
                            tube\.saumon\.io|
                            tube\.schleuss\.online|
                            tube\.schule\.social|
                            tube\.seditio\.fr|
                            tube\.shanti\.cafe|
                            tube\.shela\.nu|
                            tube\.skrep\.in|
                            tube\.sp-codes\.de|
                            tube\.sp4ke\.com|
                            tube\.superseriousbusiness\.org|
                            tube\.systest\.eu|
                            tube\.tappret\.fr|
                            tube\.tardis\.world|
                            tube\.toontoet\.nl|
                            tube\.tpshd\.de|
                            tube\.troopers\.agency|
                            tube\.tylerdavis\.xyz|
                            tube\.undernet\.uy|
                            tube\.vigilian-consulting\.nl|
                            tube\.vraphim\.com|
                            tube\.wehost\.lgbt|
                            tube\.wien\.rocks|
                            tube\.wolfe\.casa|
                            tube\.xd0\.de|
                            tube\.xy-space\.de|
                            tube\.yapbreak\.fr|
                            tubedu\.org|
                            tubes\.jodh\.us|
                            tuktube\.com|
                            turkum\.me|
                            tututu\.tube|
                            tuvideo\.encanarias\.info|
                            tv1\.cocu\.cc|
                            tv1\.gomntu\.space|
                            tv2\.cocu\.cc|
                            tv\.adn\.life|
                            tv\.atmx\.ca|
                            tv\.bitma\.st|
                            tv\.generallyrubbish\.net\.au|
                            tv\.lumbung\.space|
                            tv\.mattchristiansenmedia\.com|
                            tv\.netwhood\.online|
                            tv\.neue\.city|
                            tv\.piejacker\.net|
                            tv\.pirateradio\.social|
                            tv\.undersco\.re|
                            tvox\.ru|
                            twctube\.twc-zone\.eu|
                            unfilter\.tube|
                            v\.basspistol\.org|
                            v\.kisombrella\.top|
                            v\.lastorder\.xyz|
                            v\.lor\.sh|
                            v\.phreedom\.club|
                            v\.sil\.sh|
                            v\.szy\.io|
                            v\.xxxapex\.com|
                            veezee\.tube|
                            vid\.dascoyote\.xyz|
                            vid\.garwood\.io|
                            vid\.ncrypt\.at|
                            vid\.pravdastalina\.info|
                            vid\.qorg11\.net|
                            vid\.rajeshtaylor\.com|
                            vid\.samtripoli\.com|
                            vid\.werefox\.dev|
                            vid\.wildeboer\.net|
                            video-cave-v2\.de|
                            video\.076\.ne\.jp|
                            video\.1146\.nohost\.me|
                            video\.altertek\.org|
                            video\.anartist\.org|
                            video\.apps\.thedoodleproject\.net|
                            video\.artist\.cx|
                            video\.asgardius\.company|
                            video\.balsillie\.net|
                            video\.bards\.online|
                            video\.binarydad\.com|
                            video\.blast-info\.fr|
                            video\.catgirl\.biz|
                            video\.cigliola\.com|
                            video\.cm-en-transition\.fr|
                            video\.cnt\.social|
                            video\.coales\.co|
                            video\.codingfield\.com|
                            video\.comptoir\.net|
                            video\.comune\.trento\.it|
                            video\.cpn\.so|
                            video\.csc49\.fr|
                            video\.cybre\.town|
                            video\.demokratischer-sommer\.de|
                            video\.discord-insoumis\.fr|
                            video\.dolphincastle\.com|
                            video\.dresden\.network|
                            video\.ecole-89\.com|
                            video\.elgrillolibertario\.org|
                            video\.emergeheart\.info|
                            video\.eradicatinglove\.xyz|
                            video\.ethantheenigma\.me|
                            video\.exodus-privacy\.eu\.org|
                            video\.fbxl\.net|
                            video\.fhtagn\.org|
                            video\.greenmycity\.eu|
                            video\.guerredeclasse\.fr|
                            video\.gyt\.is|
                            video\.hackers\.town|
                            video\.hardlimit\.com|
                            video\.hooli\.co|
                            video\.igem\.org|
                            video\.internet-czas-dzialac\.pl|
                            video\.islameye\.com|
                            video\.kicik\.fr|
                            video\.kuba-orlik\.name|
                            video\.kyushojitsu\.ca|
                            video\.lavolte\.net|
                            video\.lespoesiesdheloise\.fr|
                            video\.liberta\.vip|
                            video\.liege\.bike|
                            video\.linc\.systems|
                            video\.linux\.it|
                            video\.linuxtrent\.it|
                            video\.lokal\.social|
                            video\.lono\.space|
                            video\.lunasqu\.ee|
                            video\.lundi\.am|
                            video\.marcorennmaus\.de|
                            video\.mass-trespass\.uk|
                            video\.mugoreve\.fr|
                            video\.mundodesconocido\.com|
                            video\.mycrowd\.ca|
                            video\.nogafam\.es|
                            video\.odayacres\.farm|
                            video\.ozgurkon\.org|
                            video\.p1ng0ut\.social|
                            video\.p3x\.de|
                            video\.pcf\.fr|
                            video\.pony\.gallery|
                            video\.potate\.space|
                            video\.pourpenser\.pro|
                            video\.progressiv\.dev|
                            video\.resolutions\.it|
                            video\.rw501\.de|
                            video\.screamer\.wiki|
                            video\.sdm-tools\.net|
                            video\.sftblw\.moe|
                            video\.shitposter\.club|
                            video\.skyn3t\.in|
                            video\.soi\.ch|
                            video\.stuartbrand\.co\.uk|
                            video\.thinkof\.name|
                            video\.toot\.pt|
                            video\.triplea\.fr|
                            video\.turbo\.chat|
                            video\.vaku\.org\.ua|
                            video\.veloma\.org|
                            video\.violoncello\.ch|
                            video\.wilkie\.how|
                            video\.wsf2021\.info|
                            videorelay\.co|
                            videos-passages\.huma-num\.fr|
                            videos\.3d-wolf\.com|
                            videos\.ahp-numerique\.fr|
                            videos\.alexandrebadalo\.pt|
                            videos\.archigny\.net|
                            videos\.benjaminbrady\.ie|
                            videos\.buceoluegoexisto\.com|
                            videos\.capas\.se|
                            videos\.casually\.cat|
                            videos\.cloudron\.io|
                            videos\.coletivos\.org|
                            videos\.danksquad\.org|
                            videos\.denshi\.live|
                            videos\.fromouter\.space|
                            videos\.fsci\.in|
                            videos\.globenet\.org|
                            videos\.hauspie\.fr|
                            videos\.hush\.is|
                            videos\.john-livingston\.fr|
                            videos\.jordanwarne\.xyz|
                            videos\.lavoixdessansvoix\.org|
                            videos\.leslionsfloorball\.fr|
                            videos\.lucero\.top|
                            videos\.martyn\.berlin|
                            videos\.mastodont\.cat|
                            videos\.monstro1\.com|
                            videos\.npo\.city|
                            videos\.optoutpod\.com|
                            videos\.petch\.rocks|
                            videos\.pzelawski\.xyz|
                            videos\.rampin\.org|
                            videos\.scanlines\.xyz|
                            videos\.shmalls\.pw|
                            videos\.sibear\.fr|
                            videos\.stadtfabrikanten\.org|
                            videos\.tankernn\.eu|
                            videos\.testimonia\.org|
                            videos\.thisishowidontdisappear\.com|
                            videos\.traumaheilung\.net|
                            videos\.trom\.tf|
                            videos\.wakkerewereld\.nu|
                            videos\.weblib\.re|
                            videos\.yesil\.club|
                            vids\.roshless\.me|
                            vids\.tekdmn\.me|
                            vidz\.dou\.bet|
                            vod\.lumikko\.dev|
                            vs\.uniter\.network|
                            vulgarisation-informatique\.fr|
                            watch\.breadtube\.tv|
                            watch\.deranalyst\.ch|
                            watch\.ignorance\.eu|
                            watch\.krazy\.party|
                            watch\.libertaria\.space|
                            watch\.rt4mn\.org|
                            watch\.softinio\.com|
                            watch\.tubelab\.video|
                            web-fellow\.de|
                            webtv\.vandoeuvre\.net|
                            wechill\.space|
                            wikileaks\.video|
                            wiwi\.video|
                            worldofvids\.com|
                            wwtube\.net|
                            www4\.mir\.inter21\.net|
                            www\.birkeundnymphe\.de|
                            www\.captain-german\.com|
                            www\.wiki-tube\.de|
                            xxivproduction\.video|
                            xxx\.noho\.st|

                            # from youtube-dl
                            peertube\.rainbowswingers\.net|
                            tube\.stanisic\.nl|
                            peer\.suiri\.us|
                            medias\.libox\.fr|
                            videomensoif\.ynh\.fr|
                            peertube\.travelpandas\.eu|
                            peertube\.rachetjay\.fr|
                            peertube\.montecsys\.fr|
                            tube\.eskuero\.me|
                            peer\.tube|
                            peertube\.umeahackerspace\.se|
                            tube\.nx-pod\.de|
                            video\.monsieurbidouille\.fr|
                            tube\.openalgeria\.org|
                            vid\.lelux\.fi|
                            video\.anormallostpod\.ovh|
                            tube\.crapaud-fou\.org|
                            peertube\.stemy\.me|
                            lostpod\.space|
                            exode\.me|
                            peertube\.snargol\.com|
                            vis\.ion\.ovh|
                            videosdulib\.re|
                            v\.mbius\.io|
                            videos\.judrey\.eu|
                            peertube\.osureplayviewer\.xyz|
                            peertube\.mathieufamily\.ovh|
                            www\.videos-libr\.es|
                            fightforinfo\.com|
                            peertube\.fediverse\.ru|
                            peertube\.oiseauroch\.fr|
                            video\.nesven\.eu|
                            v\.bearvideo\.win|
                            video\.qoto\.org|
                            justporn\.cc|
                            video\.vny\.fr|
                            peervideo\.club|
                            tube\.taker\.fr|
                            peertube\.chantierlibre\.org|
                            tube\.ipfixe\.info|
                            tube\.kicou\.info|
                            tube\.dodsorf\.as|
                            videobit\.cc|
                            video\.yukari\.moe|
                            videos\.elbinario\.net|
                            hkvideo\.live|
                            pt\.tux\.tf|
                            www\.hkvideo\.live|
                            FIGHTFORINFO\.com|
                            pt\.765racing\.com|
                            peertube\.gnumeria\.eu\.org|
                            nordenmedia\.com|
                            peertube\.co\.uk|
                            tube\.darfweb\.eu|
                            tube\.kalah-france\.org|
                            0ch\.in|
                            vod\.mochi\.academy|
                            film\.node9\.org|
                            peertube\.hatthieves\.es|
                            video\.fitchfamily\.org|
                            peertube\.ddns\.net|
                            video\.ifuncle\.kr|
                            video\.fdlibre\.eu|
                            tube\.22decembre\.eu|
                            peertube\.harmoniescreatives\.com|
                            tube\.fabrigli\.fr|
                            video\.thedwyers\.co|
                            video\.bruitbruit\.com|
                            peertube\.foxfam\.club|
                            peer\.philoxweb\.be|
                            videos\.bugs\.social|
                            peertube\.malbert\.xyz|
                            peertube\.bilange\.ca|
                            libretube\.net|
                            diytelevision\.com|
                            peertube\.fedilab\.app|
                            libre\.video|
                            video\.mstddntfdn\.online|
                            us\.tv|
                            peertube\.sl-network\.fr|
                            peertube\.dynlinux\.io|
                            peertube\.david\.durieux\.family|
                            peertube\.linuxrocks\.online|
                            peerwatch\.xyz|
                            v\.kretschmann\.social|
                            tube\.otter\.sh|
                            yt\.is\.nota\.live|
                            tube\.dragonpsi\.xyz|
                            peertube\.boneheadmedia\.com|
                            videos\.funkwhale\.audio|
                            watch\.44con\.com|
                            peertube\.gcaillaut\.fr|
                            peertube\.icu|
                            pony\.tube|
                            spacepub\.space|
                            tube\.stbr\.io|
                            v\.mom-gay\.faith|
                            tube\.port0\.xyz|
                            peertube\.simounet\.net|
                            play\.jergefelt\.se|
                            peertube\.zeteo\.me|
                            tube\.danq\.me|
                            peertube\.kerenon\.com|
                            tube\.fab-l3\.org|
                            tube\.calculate\.social|
                            peertube\.mckillop\.org|
                            tube\.netzspielplatz\.de|
                            vod\.ksite\.de|
                            peertube\.laas\.fr|
                            tube\.govital\.net|
                            peertube\.stephenson\.cc|
                            bistule\.nohost\.me|
                            peertube\.kajalinifi\.de|
                            video\.ploud\.jp|
                            video\.omniatv\.com|
                            peertube\.ffs2play\.fr|
                            peertube\.leboulaire\.ovh|
                            peertube\.tronic-studio\.com|
                            peertube\.public\.cat|
                            peertube\.metalbanana\.net|
                            video\.1000i100\.fr|
                            peertube\.alter-nativ-voll\.de|
                            tube\.pasa\.tf|
                            tube\.worldofhauru\.xyz|
                            pt\.kamp\.site|
                            peertube\.teleassist\.fr|
                            videos\.mleduc\.xyz|
                            conf\.tube|
                            media\.privacyinternational\.org|
                            pt\.forty-two\.nl|
                            video\.halle-leaks\.de|
                            video\.grosskopfgames\.de|
                            peertube\.schaeferit\.de|
                            peertube\.jackbot\.fr|
                            tube\.extinctionrebellion\.fr|
                            peertube\.f-si\.org|
                            video\.subak\.ovh|
                            videos\.koweb\.fr|
                            peertube\.zergy\.net|
                            peertube\.roflcopter\.fr|
                            peertube\.floss-marketing-school\.com|
                            vloggers\.social|
                            peertube\.iriseden\.eu|
                            videos\.ubuntu-paris\.org|
                            peertube\.mastodon\.host|
                            armstube\.com|
                            peertube\.s2s\.video|
                            peertube\.lol|
                            tube\.open-plug\.eu|
                            open\.tube|
                            peertube\.ch|
                            peertube\.normandie-libre\.fr|
                            peertube\.slat\.org|
                            video\.lacaveatonton\.ovh|
                            peertube\.uno|
                            peertube\.servebeer\.com|
                            peertube\.fedi\.quebec|
                            tube\.h3z\.jp|
                            tube\.plus200\.com|
                            peertube\.eric\.ovh|
                            tube\.metadocs\.cc|
                            tube\.unmondemeilleur\.eu|
                            gouttedeau\.space|
                            video\.antirep\.net|
                            nrop\.cant\.at|
                            tube\.ksl-bmx\.de|
                            tube\.plaf\.fr|
                            tube\.tchncs\.de|
                            video\.devinberg\.com|
                            hitchtube\.fr|
                            peertube\.kosebamse\.com|
                            yunopeertube\.myddns\.me|
                            peertube\.varney\.fr|
                            peertube\.anon-kenkai\.com|
                            tube\.maiti\.info|
                            tubee\.fr|
                            videos\.dinofly\.com|
                            toobnix\.org|
                            videotape\.me|
                            voca\.tube|
                            video\.heromuster\.com|
                            video\.lemediatv\.fr|
                            video\.up\.edu\.ph|
                            balafon\.video|
                            video\.ivel\.fr|
                            thickrips\.cloud|
                            pt\.laurentkruger\.fr|
                            video\.monarch-pass\.net|
                            peertube\.artica\.center|
                            video\.alternanet\.fr|
                            indymotion\.fr|
                            fanvid\.stopthatimp\.net|
                            video\.farci\.org|
                            v\.lesterpig\.com|
                            video\.okaris\.de|
                            tube\.pawelko\.net|
                            peertube\.mablr\.org|
                            tube\.fede\.re|
                            pytu\.be|
                            evertron\.tv|
                            devtube\.dev-wiki\.de|
                            raptube\.antipub\.org|
                            video\.selea\.se|
                            peertube\.mygaia\.org|
                            video\.oh14\.de|
                            peertube\.livingutopia\.org|
                            peertube\.the-penguin\.de|
                            tube\.thechangebook\.org|
                            tube\.anjara\.eu|
                            pt\.pube\.tk|
                            video\.samedi\.pm|
                            mplayer\.demouliere\.eu|
                            widemus\.de|
                            peertube\.me|
                            peertube\.zapashcanon\.fr|
                            video\.latavernedejohnjohn\.fr|
                            peertube\.pcservice46\.fr|
                            peertube\.mazzonetto\.eu|
                            video\.irem\.univ-paris-diderot\.fr|
                            video\.livecchi\.cloud|
                            alttube\.fr|
                            video\.coop\.tools|
                            video\.cabane-libre\.org|
                            peertube\.openstreetmap\.fr|
                            videos\.alolise\.org|
                            irrsinn\.video|
                            video\.antopie\.org|
                            scitech\.video|
                            tube2\.nemsia\.org|
                            video\.amic37\.fr|
                            peertube\.freeforge\.eu|
                            video\.arbitrarion\.com|
                            video\.datsemultimedia\.com|
                            stoptrackingus\.tv|
                            peertube\.ricostrongxxx\.com|
                            docker\.videos\.lecygnenoir\.info|
                            peertube\.togart\.de|
                            tube\.postblue\.info|
                            videos\.domainepublic\.net|
                            peertube\.cyber-tribal\.com|
                            video\.gresille\.org|
                            peertube\.dsmouse\.net|
                            cinema\.yunohost\.support|
                            tube\.theocevaer\.fr|
                            repro\.video|
                            tube\.4aem\.com|
                            quaziinc\.com|
                            peertube\.metawurst\.space|
                            videos\.wakapo\.com|
                            video\.ploud\.fr|
                            video\.freeradical\.zone|
                            tube\.valinor\.fr|
                            refuznik\.video|
                            pt\.kircheneuenburg\.de|
                            peertube\.asrun\.eu|
                            peertube\.lagob\.fr|
                            videos\.side-ways\.net|
                            91video\.online|
                            video\.valme\.io|
                            video\.taboulisme\.com|
                            videos-libr\.es|
                            tv\.mooh\.fr|
                            nuage\.acostey\.fr|
                            video\.monsieur-a\.fr|
                            peertube\.librelois\.fr|
                            videos\.pair2jeux\.tube|
                            videos\.pueseso\.club|
                            peer\.mathdacloud\.ovh|
                            media\.assassinate-you\.net|
                            vidcommons\.org|
                            ptube\.rousset\.nom\.fr|
                            tube\.cyano\.at|
                            videos\.squat\.net|
                            video\.iphodase\.fr|
                            peertube\.makotoworkshop\.org|
                            peertube\.serveur\.slv-valbonne\.fr|
                            vault\.mle\.party|
                            hostyour\.tv|
                            videos\.hack2g2\.fr|
                            libre\.tube|
                            pire\.artisanlogiciel\.net|
                            videos\.numerique-en-commun\.fr|
                            video\.netsyms\.com|
                            video\.die-partei\.social|
                            video\.writeas\.org|
                            peertube\.swarm\.solvingmaz\.es|
                            tube\.pericoloso\.ovh|
                            watching\.cypherpunk\.observer|
                            videos\.adhocmusic\.com|
                            tube\.rfc1149\.net|
                            peertube\.librelabucm\.org|
                            videos\.numericoop\.fr|
                            peertube\.koehn\.com|
                            peertube\.anarchmusicall\.net|
                            tube\.kampftoast\.de|
                            vid\.y-y\.li|
                            peertube\.xtenz\.xyz|
                            diode\.zone|
                            tube\.egf\.mn|
                            peertube\.nomagic\.uk|
                            visionon\.tv|
                            videos\.koumoul\.com|
                            video\.rastapuls\.com|
                            video\.mantlepro\.com|
                            video\.deadsuperhero\.com|
                            peertube\.musicstudio\.pro|
                            peertube\.we-keys\.fr|
                            artitube\.artifaille\.fr|
                            peertube\.ethernia\.net|
                            tube\.midov\.pl|
                            peertube\.fr|
                            watch\.snoot\.tube|
                            peertube\.donnadieu\.fr|
                            argos\.aquilenet\.fr|
                            tube\.nemsia\.org|
                            tube\.bruniau\.net|
                            videos\.darckoune\.moe|
                            tube\.traydent\.info|
                            dev\.videos\.lecygnenoir\.info|
                            peertube\.nayya\.org|
                            peertube\.live|
                            peertube\.mofgao\.space|
                            video\.lequerrec\.eu|
                            peertube\.amicale\.net|
                            aperi\.tube|
                            tube\.ac-lyon\.fr|
                            video\.lw1\.at|
                            www\.yiny\.org|
                            videos\.pofilo\.fr|
                            tube\.lou\.lt|
                            choob\.h\.etbus\.ch|
                            tube\.hoga\.fr|
                            peertube\.heberge\.fr|
                            video\.obermui\.de|
                            videos\.cloudfrancois\.fr|
                            betamax\.video|
                            video\.typica\.us|
                            tube\.piweb\.be|
                            video\.blender\.org|
                            peertube\.cat|
                            tube\.kdy\.ch|
                            pe\.ertu\.be|
                            peertube\.social|
                            videos\.lescommuns\.org|
                            tv\.datamol\.org|
                            videonaute\.fr|
                            dialup\.express|
                            peertube\.nogafa\.org|
                            megatube\.lilomoino\.fr|
                            peertube\.tamanoir\.foucry\.net|
                            peertube\.devosi\.org|
                            peertube\.1312\.media|
                            tube\.bootlicker\.party|
                            skeptikon\.fr|
                            video\.blueline\.mg|
                            tube\.homecomputing\.fr|
                            tube\.ouahpiti\.info|
                            video\.tedomum\.net|
                            video\.g3l\.org|
                            fontube\.fr|
                            peertube\.gaialabs\.ch|
                            tube\.kher\.nl|
                            peertube\.qtg\.fr|
                            video\.migennes\.net|
                            tube\.p2p\.legal|
                            troll\.tv|
                            videos\.iut-orsay\.fr|
                            peertube\.solidev\.net|
                            videos\.cemea\.org|
                            video\.passageenseine\.fr|
                            videos\.festivalparminous\.org|
                            peertube\.touhoppai\.moe|
                            sikke\.fi|
                            peer\.hostux\.social|
                            share\.tube|
                            peertube\.walkingmountains\.fr|
                            videos\.benpro\.fr|
                            peertube\.parleur\.net|
                            peertube\.heraut\.eu|
                            tube\.aquilenet\.fr|
                            peertube\.gegeweb\.eu|
                            framatube\.org|
                            thinkerview\.video|
                            tube\.conferences-gesticulees\.net|
                            peertube\.datagueule\.tv|
                            video\.lqdn\.fr|
                            tube\.mochi\.academy|
                            media\.zat\.im|
                            video\.colibris-outilslibres\.org|
                            tube\.svnet\.fr|
                            peertube\.video|
                            peertube2\.cpy\.re|
                            peertube3\.cpy\.re|
                            videos\.tcit\.fr|
                            peertube\.cpy\.re|
                            canard\.tube
                        )'''
    _UUID_RE = r'[\da-zA-Z]{22}|[\da-fA-F]{8}-[\da-fA-F]{4}-[\da-fA-F]{4}-[\da-fA-F]{4}-[\da-fA-F]{12}'
    _API_BASE = 'https://%s/api/v1/videos/%s/%s'
    _VALID_URL = r'''(?x)
                    (?:
                        peertube:(?P<host>[^:]+):|
                        https?://(?P<host_2>%s)/(?:videos/(?:watch|embed)|api/v\d/videos|w)/
                    )
                    (?P<id>%s)
                    ''' % (_INSTANCES_RE, _UUID_RE)
    _TESTS = [{
        'url': 'https://framatube.org/videos/watch/9c9de5e8-0a1e-484a-b099-e80766180a6d',
        'md5': '8563064d245a4be5705bddb22bb00a28',
        'info_dict': {
            'id': '9c9de5e8-0a1e-484a-b099-e80766180a6d',
            'ext': 'mp4',
            'title': 'What is PeerTube?',
            'description': 'md5:3fefb8dde2b189186ce0719fda6f7b10',
            'thumbnail': r're:https?://.*\.(?:jpg|png)',
            'timestamp': 1538391166,
            'upload_date': '20181001',
            'uploader': 'Framasoft',
            'uploader_id': '3',
            'uploader_url': 'https://framatube.org/accounts/framasoft',
            'channel': 'A propos de PeerTube',
            'channel_id': '2215',
            'channel_url': 'https://framatube.org/video-channels/joinpeertube',
            'language': 'en',
            'license': 'Attribution - Share Alike',
            'duration': 113,
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'tags': ['framasoft', 'peertube'],
            'categories': ['Science & Technology'],
        }
    }, {
        'url': 'https://peertube2.cpy.re/w/122d093a-1ede-43bd-bd34-59d2931ffc5e',
        'info_dict': {
            'id': '122d093a-1ede-43bd-bd34-59d2931ffc5e',
            'ext': 'mp4',
            'title': 'E2E tests',
            'uploader_id': '37855',
            'timestamp': 1589276219,
            'upload_date': '20200512',
            'uploader': 'chocobozzz',
        }
    }, {
        'url': 'https://peertube2.cpy.re/w/3fbif9S3WmtTP8gGsC5HBd',
        'info_dict': {
            'id': '3fbif9S3WmtTP8gGsC5HBd',
            'ext': 'mp4',
            'title': 'E2E tests',
            'uploader_id': '37855',
            'timestamp': 1589276219,
            'upload_date': '20200512',
            'uploader': 'chocobozzz',
        },
    }, {
        'url': 'https://peertube2.cpy.re/api/v1/videos/3fbif9S3WmtTP8gGsC5HBd',
        'info_dict': {
            'id': '3fbif9S3WmtTP8gGsC5HBd',
            'ext': 'mp4',
            'title': 'E2E tests',
            'uploader_id': '37855',
            'timestamp': 1589276219,
            'upload_date': '20200512',
            'uploader': 'chocobozzz',
        },
    }, {
        # Issue #26002
        'url': 'peertube:spacepub.space:d8943b2d-8280-497b-85ec-bc282ec2afdc',
        'info_dict': {
            'id': 'd8943b2d-8280-497b-85ec-bc282ec2afdc',
            'ext': 'mp4',
            'title': 'Dot matrix printer shell demo',
            'uploader_id': '3',
            'timestamp': 1587401293,
            'upload_date': '20200420',
            'uploader': 'Drew DeVault',
        }
    }, {
        'url': 'https://peertube.debian.social/videos/watch/0b04f13d-1e18-4f1d-814e-4979aa7c9c44',
        'only_matching': True,
    }, {
        # nsfw
        'url': 'https://vod.ksite.de/videos/watch/9bb88cd3-9959-46d9-9ab9-33d2bb704c39',
        'only_matching': True,
    }, {
        'url': 'https://vod.ksite.de/videos/embed/fed67262-6edb-4d1c-833b-daa9085c71d7',
        'only_matching': True,
    }, {
        'url': 'https://peertube.tv/api/v1/videos/c1875674-97d0-4c94-a058-3f7e64c962e8',
        'only_matching': True,
    }, {
        'url': 'peertube:framatube.org:b37a5b9f-e6b5-415c-b700-04a5cd6ec205',
        'only_matching': True,
    }]

    @staticmethod
    def _extract_peertube_url(webpage, source_url):
        mobj = re.match(
            r'https?://(?P<host>[^/]+)/(?:videos/(?:watch|embed)|w)/(?P<id>%s)'
            % PeerTubeIE._UUID_RE, source_url)
        if mobj and any(p in webpage for p in (
                'meta property="og:platform" content="PeerTube"',
                '<title>PeerTube<',
                'There will be other non JS-based clients to access PeerTube',
                '>We are sorry but it seems that PeerTube is not compatible with your web browser.<')):
            return 'peertube:%s:%s' % mobj.group('host', 'id')

    @staticmethod
    def _extract_urls(webpage, source_url):
        entries = re.findall(
            r'''(?x)<iframe[^>]+\bsrc=["\'](?P<url>(?:https?:)?//%s/videos/embed/%s)'''
            % (PeerTubeIE._INSTANCES_RE, PeerTubeIE._UUID_RE), webpage)
        if not entries:
            peertube_url = PeerTubeIE._extract_peertube_url(webpage, source_url)
            if peertube_url:
                entries = [peertube_url]
        return entries

    def _call_api(self, host, video_id, path, note=None, errnote=None, fatal=True):
        return self._download_json(
            self._API_BASE % (host, video_id, path), video_id,
            note=note, errnote=errnote, fatal=fatal)

    def _get_subtitles(self, host, video_id):
        captions = self._call_api(
            host, video_id, 'captions', note='Downloading captions JSON',
            fatal=False)
        if not isinstance(captions, dict):
            return
        data = captions.get('data')
        if not isinstance(data, list):
            return
        subtitles = {}
        for e in data:
            language_id = try_get(e, lambda x: x['language']['id'], compat_str)
            caption_url = urljoin('https://%s' % host, e.get('captionPath'))
            if not caption_url:
                continue
            subtitles.setdefault(language_id or 'en', []).append({
                'url': caption_url,
            })
        return subtitles

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        host = mobj.group('host') or mobj.group('host_2')
        video_id = mobj.group('id')

        video = self._call_api(
            host, video_id, '', note='Downloading video JSON')

        title = video['name']

        formats = []
        files = video.get('files') or []
        for playlist in (video.get('streamingPlaylists') or []):
            if not isinstance(playlist, dict):
                continue
            playlist_files = playlist.get('files')
            if not (playlist_files and isinstance(playlist_files, list)):
                continue
            files.extend(playlist_files)
        for file_ in files:
            if not isinstance(file_, dict):
                continue
            file_url = url_or_none(file_.get('fileUrl'))
            if not file_url:
                continue
            file_size = int_or_none(file_.get('size'))
            format_id = try_get(
                file_, lambda x: x['resolution']['label'], compat_str)
            f = parse_resolution(format_id)
            f.update({
                'url': file_url,
                'format_id': format_id,
                'filesize': file_size,
            })
            if format_id == '0p':
                f['vcodec'] = 'none'
            else:
                f['fps'] = int_or_none(file_.get('fps'))
            formats.append(f)
        self._sort_formats(formats)

        description = video.get('description')
        if description and len(description) >= 250:
            # description is shortened
            full_description = self._call_api(
                host, video_id, 'description', note='Downloading description JSON',
                fatal=False)

            if isinstance(full_description, dict):
                description = str_or_none(full_description.get('description')) or description

        subtitles = self.extract_subtitles(host, video_id)

        def data(section, field, type_):
            return try_get(video, lambda x: x[section][field], type_)

        def account_data(field, type_):
            return data('account', field, type_)

        def channel_data(field, type_):
            return data('channel', field, type_)

        category = data('category', 'label', compat_str)
        categories = [category] if category else None

        nsfw = video.get('nsfw')
        if nsfw is bool:
            age_limit = 18 if nsfw else 0
        else:
            age_limit = None

        webpage_url = 'https://%s/videos/watch/%s' % (host, video_id)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': urljoin(webpage_url, video.get('thumbnailPath')),
            'timestamp': unified_timestamp(video.get('publishedAt')),
            'uploader': account_data('displayName', compat_str),
            'uploader_id': str_or_none(account_data('id', int)),
            'uploader_url': url_or_none(account_data('url', compat_str)),
            'channel': channel_data('displayName', compat_str),
            'channel_id': str_or_none(channel_data('id', int)),
            'channel_url': url_or_none(channel_data('url', compat_str)),
            'language': data('language', 'id', compat_str),
            'license': data('licence', 'label', compat_str),
            'duration': int_or_none(video.get('duration')),
            'view_count': int_or_none(video.get('views')),
            'like_count': int_or_none(video.get('likes')),
            'dislike_count': int_or_none(video.get('dislikes')),
            'age_limit': age_limit,
            'tags': try_get(video, lambda x: x['tags'], list),
            'categories': categories,
            'formats': formats,
            'subtitles': subtitles,
            'webpage_url': webpage_url,
        }


class PeerTubePlaylistIE(InfoExtractor):
    IE_NAME = 'PeerTube:Playlist'
    _TYPES = {
        'a': 'accounts',
        'c': 'video-channels',
        'w/p': 'video-playlists',
    }
    _VALID_URL = r'''(?x)
                        https?://(?P<host>%s)/(?P<type>(?:%s))/
                    (?P<id>[^/]+)
                    ''' % (PeerTubeIE._INSTANCES_RE, '|'.join(_TYPES.keys()))
    _TESTS = [{
        'url': 'https://peertube.tux.ovh/w/p/3af94cba-95e8-4b74-b37a-807ab6d82526',
        'info_dict': {
            'id': '3af94cba-95e8-4b74-b37a-807ab6d82526',
            'description': 'playlist',
            'timestamp': 1611171863,
            'title': 'playlist',
        },
        'playlist_mincount': 6,
    }, {
        'url': 'https://peertube.tux.ovh/w/p/wkyqcQBnsvFxtUB2pkYc1e',
        'info_dict': {
            'id': 'wkyqcQBnsvFxtUB2pkYc1e',
            'description': 'Cette liste de vidéos contient uniquement les jeux qui peuvent être terminés en une seule vidéo.',
            'title': 'Let\'s Play',
            'timestamp': 1604147331,
        },
        'playlist_mincount': 6,
    }, {
        'url': 'https://peertube.debian.social/w/p/hFdJoTuyhNJVa1cDWd1d12',
        'info_dict': {
            'id': 'hFdJoTuyhNJVa1cDWd1d12',
            'description': 'Diversas palestras do Richard Stallman no Brasil.',
            'title': 'Richard Stallman no Brasil',
            'timestamp': 1599676222,
        },
        'playlist_mincount': 9,
    }, {
        'url': 'https://peertube2.cpy.re/a/chocobozzz/videos',
        'info_dict': {
            'id': 'chocobozzz',
            'timestamp': 1553874564,
            'title': 'chocobozzz',
        },
        'playlist_mincount': 2,
    }, {
        'url': 'https://framatube.org/c/bf54d359-cfad-4935-9d45-9d6be93f63e8/videos',
        'info_dict': {
            'id': 'bf54d359-cfad-4935-9d45-9d6be93f63e8',
            'timestamp': 1519917377,
            'title': 'Les vidéos de Framasoft',
        },
        'playlist_mincount': 345,
    }, {
        'url': 'https://peertube2.cpy.re/c/blender_open_movies@video.blender.org/videos',
        'info_dict': {
            'id': 'blender_open_movies@video.blender.org',
            'timestamp': 1542287810,
            'title': 'Official Blender Open Movies',
        },
        'playlist_mincount': 11,
    }]
    _API_BASE = 'https://%s/api/v1/%s/%s%s'
    _PAGE_SIZE = 30

    def call_api(self, host, name, path, base, **kwargs):
        return self._download_json(
            self._API_BASE % (host, base, name, path), name, **kwargs)

    def fetch_page(self, host, id, type, page):
        page += 1
        video_data = self.call_api(
            host, id,
            f'/videos?sort=-createdAt&start={self._PAGE_SIZE * (page - 1)}&count={self._PAGE_SIZE}&nsfw=both',
            type, note=f'Downloading page {page}').get('data', [])
        for video in video_data:
            shortUUID = video.get('shortUUID') or try_get(video, lambda x: x['video']['shortUUID'])
            video_title = video.get('name') or try_get(video, lambda x: x['video']['name'])
            yield self.url_result(
                f'https://{host}/w/{shortUUID}', PeerTubeIE.ie_key(),
                video_id=shortUUID, video_title=video_title)

    def _extract_playlist(self, host, type, id):
        info = self.call_api(host, id, '', type, note='Downloading playlist information', fatal=False)

        playlist_title = info.get('displayName')
        playlist_description = info.get('description')
        playlist_timestamp = unified_timestamp(info.get('createdAt'))
        channel = try_get(info, lambda x: x['ownerAccount']['name']) or info.get('displayName')
        channel_id = try_get(info, lambda x: x['ownerAccount']['id']) or info.get('id')
        thumbnail = format_field(info, 'thumbnailPath', f'https://{host}%s')

        entries = OnDemandPagedList(functools.partial(
            self.fetch_page, host, id, type), self._PAGE_SIZE)

        return self.playlist_result(
            entries, id, playlist_title, playlist_description,
            timestamp=playlist_timestamp, channel=channel, channel_id=channel_id, thumbnail=thumbnail)

    def _real_extract(self, url):
        type, host, id = self._match_valid_url(url).group('type', 'host', 'id')
        type = self._TYPES[type]
        return self._extract_playlist(host, type, id)
