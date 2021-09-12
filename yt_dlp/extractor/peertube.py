# coding: utf-8
from __future__ import unicode_literals

import functools
import re

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
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
                            0ch\.in|
                            40two\.tube|
                            91video\.online|
                            FIGHTFORINFO\.com|
                            a\.metube\.ch|
                            advtv\.ml|
                            algorithmic\.tv|
                            alimulama\.com|
                            alttube\.fr|
                            aperi\.tube|
                            arcana\.fun|
                            archive\.vidicon\.org|
                            argos\.aquilenet\.fr|
                            armstube\.com|
                            artefac-paris\.tv|
                            artitube\.artifaille\.fr|
                            auf1\.eu|
                            balafon\.video|
                            battlepenguin\.video|
                            beertube\.epgn\.ch|
                            befree\.nohost\.me|
                            betamax\.video|
                            bideoak\.argia\.eus|
                            birkeundnymphe\.de|
                            bistule\.nohost\.me|
                            bitcointv\.com|
                            canard\.tube|
                            cattube\.org|
                            choob\.h\.etbus\.ch|
                            cinema\.yunohost\.support|
                            clap\.nerv-project\.eu|
                            climatejustice\.video|
                            comf\.tube|
                            conf\.tube|
                            conspiracydistillery\.com|
                            darkvapor\.nohost\.me|
                            daschauher\.aksel\.rocks|
                            dev\.videos\.lecygnenoir\.info|
                            devtube\.dev-wiki\.de|
                            dialup\.express|
                            digitalcourage\.video|
                            diode\.zone|
                            diytelevision\.com|
                            docker\.videos\.lecygnenoir\.info|
                            dreiecksnebel\.alex-detsch\.de|
                            eduvid\.org|
                            evangelisch\.video|
                            evertron\.tv|
                            exo\.tube|
                            exode\.me|
                            fair\.tube|
                            fanvid\.stopthatimp\.net|
                            fediverse\.tv|
                            fightforinfo\.com|
                            film\.k-prod\.fr|
                            film\.node9\.org|
                            flim\.txmn\.tk|
                            fontube\.fr|
                            fotogramas\.politicaconciencia\.org|
                            framatube\.org|
                            ftsi\.ru|
                            gary\.vger\.cloud|
                            gouttedeau\.space|
                            graeber\.video|
                            greatview\.video|
                            grypstube\.uni-greifswald\.de|
                            highvoltage\.tv|
                            hitchtube\.fr|
                            hkvideo\.live|
                            hostyour\.tv|
                            hpstube\.fr|
                            htp\.live|
                            hyperreal\.tube|
                            indymotion\.fr|
                            irrsinn\.video|
                            juggling\.digital|
                            justporn\.cc|
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
                            libre\.tube|
                            libre\.video|
                            libremedia\.video|
                            libretube\.net|
                            live\.libratoi\.org|
                            live\.nanao\.moe|
                            live\.toobnix\.org|
                            livegram\.net|
                            lolitube\.freedomchan\.moe|
                            lostpod\.space|
                            lucarne\.balsamine\.be|
                            maindreieck-tv\.de|
                            mani\.tube|
                            manicphase\.me|
                            media\.assassinate-you\.net|
                            media\.gzevd\.de|
                            media\.inno3\.cricket|
                            media\.kaitaia\.life|
                            media\.krashboyz\.org|
                            media\.over-world\.org|
                            media\.privacyinternational\.org|
                            media\.skewed\.de|
                            media\.undeadnetwork\.de|
                            media\.zat\.im|
                            medias\.libox\.fr|
                            medias\.pingbase\.net|
                            megatube\.lilomoino\.fr|
                            melsungen\.peertube-host\.de|
                            mirametube\.fr|
                            mojotube\.net|
                            monplaisirtube\.ddns\.net|
                            mountaintown\.video|
                            mplayer\.demouliere\.eu|
                            my\.bunny\.cafe|
                            myfreetube\.de|
                            mytube\.kn-cloud\.de|
                            mytube\.madzel\.de|
                            myworkoutarenapeertube\.cf|
                            nanawel-peertube\.dyndns\.org|
                            nastub\.cz|
                            nordenmedia\.com|
                            nrop\.cant\.at|
                            nuage\.acostey\.fr|
                            offenes\.tv|
                            open\.tube|
                            orgdup\.media|
                            ovaltube\.codinglab\.ch|
                            p2ptv\.ru|
                            p\.eertu\.be|
                            p\.lu|
                            pe\.ertu\.be|
                            peer\.azurs\.fr|
                            peer\.hostux\.social|
                            peer\.mathdacloud\.ovh|
                            peer\.philoxweb\.be|
                            peer\.suiri\.us|
                            peer\.tube|
                            peertube1\.zeteo\.me|
                            peertube2\.cpy\.re|
                            peertube3\.cpy\.re|
                            peertube\.020\.pl|
                            peertube\.0x5e\.eu|
                            peertube\.1312\.media|
                            peertube\.alpharius\.io|
                            peertube\.alter-nativ-voll\.de|
                            peertube\.am-networks\.fr|
                            peertube\.amicale\.net|
                            peertube\.anarchmusicall\.net|
                            peertube\.anduin\.net|
                            peertube\.anon-kenkai\.com|
                            peertube\.anzui\.dev|
                            peertube\.arbleizez\.bzh|
                            peertube\.art3mis\.de|
                            peertube\.artica\.center|
                            peertube\.asrun\.eu|
                            peertube\.atilla\.org|
                            peertube\.atsuchan\.page|
                            peertube\.aukfood\.net|
                            peertube\.aventer\.biz|
                            peertube\.b38\.rural-it\.org|
                            peertube\.beeldengeluid\.nl|
                            peertube\.be|
                            peertube\.bgzashtita\.es|
                            peertube\.bilange\.ca|
                            peertube\.bitsandlinux\.com|
                            peertube\.biz|
                            peertube\.boba\.best|
                            peertube\.boneheadmedia\.com|
                            peertube\.br0\.fr|
                            peertube\.bridaahost\.ynh\.fr|
                            peertube\.bubbletea\.dev|
                            peertube\.bubuit\.net|
                            peertube\.cabaal\.net|
                            peertube\.cats-home\.net|
                            peertube\.cat|
                            peertube\.chantierlibre\.org|
                            peertube\.chemnitz\.freifunk\.net|
                            peertube\.chevro\.fr|
                            peertube\.chrisspiegl\.com|
                            peertube\.chtisurel\.net|
                            peertube\.ch|
                            peertube\.cipherbliss\.com|
                            peertube\.cloud\.sans\.pub|
                            peertube\.co\.uk|
                            peertube\.cpge-brizeux\.fr|
                            peertube\.cpy\.re|
                            peertube\.ctseuro\.com|
                            peertube\.cuatrolibertades\.org|
                            peertube\.cyber-tribal\.com|
                            peertube\.cybercirujas\.club|
                            peertube\.cythin\.com|
                            peertube\.datagueule\.tv|
                            peertube\.david\.durieux\.family|
                            peertube\.davigge\.com|
                            peertube\.dc\.pini\.fr|
                            peertube\.ddns\.net|
                            peertube\.debian\.social|
                            peertube\.demonix\.fr|
                            peertube\.designersethiques\.org|
                            peertube\.desmu\.fr|
                            peertube\.devloprog\.org|
                            peertube\.devol\.it|
                            peertube\.devosi\.org|
                            peertube\.donnadieu\.fr|
                            peertube\.dsmouse\.net|
                            peertube\.dtmf\.ca|
                            peertube\.dynlinux\.io|
                            peertube\.ecologie\.bzh|
                            peertube\.eric\.ovh|
                            peertube\.ethernia\.net|
                            peertube\.eu\.org|
                            peertube\.european-pirates\.eu|
                            peertube\.euskarabildua\.eus|
                            peertube\.f-si\.org|
                            peertube\.fedi\.quebec|
                            peertube\.fedilab\.app|
                            peertube\.fediverse\.ru|
                            peertube\.fenarinarsa\.com|
                            peertube\.ffs2play\.fr|
                            peertube\.floss-marketing-school\.com|
                            peertube\.fomin\.site|
                            peertube\.forsud\.be|
                            peertube\.foxfam\.club|
                            peertube\.francoispelletier\.org|
                            peertube\.freeforge\.eu|
                            peertube\.freenet\.ru|
                            peertube\.freetalklive\.com|
                            peertube\.fr|
                            peertube\.functional\.cafe|
                            peertube\.gaialabs\.ch|
                            peertube\.gardeludwig\.fr|
                            peertube\.gargantia\.fr|
                            peertube\.gcaillaut\.fr|
                            peertube\.gcfamily\.fr|
                            peertube\.gegeweb\.eu|
                            peertube\.genma\.fr|
                            peertube\.get-racing\.de|
                            peertube\.gidikroon\.eu|
                            peertube\.gnumeria\.eu\.org|
                            peertube\.gruezishop\.ch|
                            peertube\.habets\.house|
                            peertube\.hackerfraternity\.org|
                            peertube\.harmoniescreatives\.com|
                            peertube\.hatthieves\.es|
                            peertube\.heberge\.fr|
                            peertube\.heraut\.eu|
                            peertube\.ichigo\.everydayimshuflin\.com|
                            peertube\.icu|
                            peertube\.ignifi\.me|
                            peertube\.inapurna\.org|
                            peertube\.informaction\.info|
                            peertube\.interhop\.org|
                            peertube\.iriseden\.eu|
                            peertube\.iselfhost\.com|
                            peertube\.it|
                            peertube\.jackbot\.fr|
                            peertube\.jensdiemer\.de|
                            peertube\.joffreyverd\.fr|
                            peertube\.kajalinifi\.de|
                            peertube\.kalua\.im|
                            peertube\.kathryl\.fr|
                            peertube\.keazilla\.net|
                            peertube\.kerenon\.com|
                            peertube\.klaewyss\.fr|
                            peertube\.kodcast\.com|
                            peertube\.koehn\.com|
                            peertube\.kosebamse\.com|
                            peertube\.kx\.studio|
                            peertube\.laas\.fr|
                            peertube\.lagob\.fr|
                            peertube\.lagvoid\.com|
                            peertube\.lavallee\.tech|
                            peertube\.le5emeaxe\.fr|
                            peertube\.leboulaire\.ovh|
                            peertube\.lestutosdeprocessus\.fr|
                            peertube\.librelabucm\.org|
                            peertube\.librelois\.fr|
                            peertube\.librenet\.co\.za|
                            peertube\.linuxrocks\.online|
                            peertube\.live|
                            peertube\.livingutopia\.org|
                            peertube\.logilab\.fr|
                            peertube\.lol|
                            peertube\.louisematic\.site|
                            peertube\.luckow\.org|
                            peertube\.luga\.at|
                            peertube\.lyceeconnecte\.fr|
                            peertube\.mablr\.org|
                            peertube\.makotoworkshop\.org|
                            peertube\.malbert\.xyz|
                            peertube\.manalejandro\.com|
                            peertube\.marud\.fr|
                            peertube\.mastodon\.host|
                            peertube\.mathieufamily\.ovh|
                            peertube\.mattone\.net|
                            peertube\.maxweiss\.io|
                            peertube\.mazzonetto\.eu|
                            peertube\.mckillop\.org|
                            peertube\.metalbanana\.net|
                            peertube\.metawurst\.space|
                            peertube\.me|
                            peertube\.mofgao\.space|
                            peertube\.monlycee\.net|
                            peertube\.montecsys\.fr|
                            peertube\.musicstudio\.pro|
                            peertube\.mxinfo\.fr|
                            peertube\.mygaia\.org|
                            peertube\.myrasp\.eu|
                            peertube\.nayya\.org|
                            peertube\.nebelcloud\.de|
                            peertube\.netzbegruenung\.de|
                            peertube\.newsocial\.tech|
                            peertube\.nicolastissot\.fr|
                            peertube\.nogafa\.org|
                            peertube\.nomagic\.uk|
                            peertube\.normandie-libre\.fr|
                            peertube\.nz|
                            peertube\.offerman\.com|
                            peertube\.oiseauroch\.fr|
                            peertube\.opencloud\.lu|
                            peertube\.openstreetmap\.fr|
                            peertube\.orthus\.link|
                            peertube\.osureplayviewer\.xyz|
                            peertube\.parleur\.net|
                            peertube\.patapouf\.xyz|
                            peertube\.pcservice46\.fr|
                            peertube\.pi2\.dev|
                            peertube\.plataformess\.org|
                            peertube\.pl|
                            peertube\.portaesgnos\.org|
                            peertube\.public\.cat|
                            peertube\.qtg\.fr|
                            peertube\.r2\.enst\.fr|
                            peertube\.r5c3\.fr|
                            peertube\.rachetjay\.fr|
                            peertube\.radres\.xyz|
                            peertube\.rainbowswingers\.net|
                            peertube\.red|
                            peertube\.ricostrongxxx\.com|
                            peertube\.robonomics\.network|
                            peertube\.roflcopter\.fr|
                            peertube\.rtnkv\.cloud|
                            peertube\.runfox\.tk|
                            peertube\.s2s\.video|
                            peertube\.satoshishop\.de|
                            peertube\.schaeferit\.de|
                            peertube\.scic-tetris\.org|
                            peertube\.securitymadein\.lu|
                            peertube\.semweb\.pro|
                            peertube\.servebeer\.com|
                            peertube\.serveur\.slv-valbonne\.fr|
                            peertube\.simounet\.net|
                            peertube\.sl-network\.fr|
                            peertube\.slat\.org|
                            peertube\.snargol\.com|
                            peertube\.social\.my-wan\.de|
                            peertube\.social|
                            peertube\.solidev\.net|
                            peertube\.soykaf\.org|
                            peertube\.stefofficiel\.me|
                            peertube\.stemy\.me|
                            peertube\.stephenson\.cc|
                            peertube\.stream|
                            peertube\.su|
                            peertube\.swarm\.solvingmaz\.es|
                            peertube\.swrs\.net|
                            peertube\.takeko\.cyou|
                            peertube\.tamanoir\.foucry\.net|
                            peertube\.tangentfox\.com|
                            peertube\.taxinachtegel\.de|
                            peertube\.teleassist\.fr|
                            peertube\.the-penguin\.de|
                            peertube\.thenewoil\.xyz|
                            peertube\.ti-fr\.com|
                            peertube\.tiennot\.net|
                            peertube\.togart\.de|
                            peertube\.touhoppai\.moe|
                            peertube\.travelpandas\.eu|
                            peertube\.troback\.com|
                            peertube\.tronic-studio\.com|
                            peertube\.tspu\.edu\.ru|
                            peertube\.tux\.ovh|
                            peertube\.tv|
                            peertube\.tweb\.tv|
                            peertube\.ucy\.de|
                            peertube\.umeahackerspace\.se|
                            peertube\.underworld\.fr|
                            peertube\.uno|
                            peertube\.us\.to|
                            peertube\.varney\.fr|
                            peertube\.ventresmous\.fr|
                            peertube\.video|
                            peertube\.vlaki\.cz|
                            peertube\.w\.utnw\.de|
                            peertube\.walkingmountains\.fr|
                            peertube\.we-keys\.fr|
                            peertube\.westring\.digital|
                            peertube\.xtenz\.xyz|
                            peertube\.xwiki\.com|
                            peertube\.zapashcanon\.fr|
                            peertube\.zergy\.net|
                            peertube\.zeteo\.me|
                            peertube\.zoz-serv\.org|
                            peervideo\.club|
                            peervideo\.ru|
                            peerwatch\.xyz|
                            periscope\.numenaute\.org|
                            perron-tube\.de|
                            petitlutinartube\.fr|
                            phijkchu\.com|
                            pierre\.tube|
                            piraten\.space|
                            pire\.artisanlogiciel\.net|
                            play\.jergefelt\.se|
                            play\.rosano\.ca|
                            player\.ojamajo\.moe|
                            plextube\.nl|
                            pocketnetpeertube1\.nohost\.me|
                            pocketnetpeertube3\.nohost\.me|
                            pocketnetpeertube4\.nohost\.me|
                            pocketnetpeertube5\.nohost\.me|
                            pocketnetpeertube6\.nohost\.me|
                            pony\.tube|
                            pt\.24-7\.ro|
                            pt\.765racing\.com|
                            pt\.apathy\.top|
                            pt\.diaspodon\.fr|
                            pt\.fedi\.tech|
                            pt\.forty-two\.nl|
                            pt\.kamp\.site|
                            pt\.kircheneuenburg\.de|
                            pt\.laurentkruger\.fr|
                            pt\.maciej\.website|
                            pt\.pube\.tk|
                            pt\.tux\.tf|
                            ptb\.lunarviews\.net|
                            ptmir1\.inter21\.net|
                            ptmir2\.inter21\.net|
                            ptmir3\.inter21\.net|
                            ptmir4\.inter21\.net|
                            ptmir5\.inter21\.net|
                            ptube\.horsentiers\.fr|
                            ptube\.rousset\.nom\.fr|
                            ptube\.xmanifesto\.club|
                            pytu\.be|
                            quaziinc\.com|
                            queermotion\.org|
                            raptube\.antipub\.org|
                            re-wizja\.re-medium\.com|
                            refuznik\.video|
                            regarder\.sans\.pub|
                            repro\.video|
                            ruraletv\.ovh|
                            s1\.gegenstimme\.tv|
                            s2\.veezee\.tube|
                            scitech\.video|
                            sdmtube\.fr|
                            sender-fm\.veezee\.tube|
                            serv1\.wiki-tube\.de|
                            serv3\.wiki-tube\.de|
                            share\.tube|
                            sickstream\.net|
                            sikke\.fi|
                            skeptikon\.fr|
                            sleepy\.tube|
                            sovran\.video|
                            spacepub\.space|
                            spectra\.video|
                            stoptrackingus\.tv|
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
                            thickrips\.cloud|
                            thinkerview\.video|
                            tilvids\.com|
                            toob\.bub\.org|
                            toobnix\.org|
                            tpaw\.video|
                            troll\.tv|
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
                            tube2\.nemsia\.org|
                            tube\.22decembre\.eu|
                            tube\.4aem\.com|
                            tube\.abolivier\.bzh|
                            tube\.ac-amiens\.fr|
                            tube\.ac-lyon\.fr|
                            tube\.aerztefueraufklaerung\.de|
                            tube\.alexx\.ml|
                            tube\.amic37\.fr|
                            tube\.anjara\.eu|
                            tube\.anufrij\.de|
                            tube\.apolut\.net|
                            tube\.aquilenet\.fr|
                            tube\.arkhalabs\.io|
                            tube\.arthack\.nz|
                            tube\.as211696\.net|
                            tube\.avensio\.de|
                            tube\.azbyka\.ru|
                            tube\.azkware\.net|
                            tube\.bachaner\.fr|
                            tube\.bmesh\.org|
                            tube\.bootlicker\.party|
                            tube\.borked\.host|
                            tube\.bruniau\.net|
                            tube\.bstly\.de|
                            tube\.calculate\.social|
                            tube\.chaoszone\.tv|
                            tube\.chatelet\.ovh|
                            tube\.cloud-libre\.eu|
                            tube\.cms\.garden|
                            tube\.conferences-gesticulees\.net|
                            tube\.cowfee\.moe|
                            tube\.crapaud-fou\.org|
                            tube\.cryptography\.dog|
                            tube\.cyano\.at|
                            tube\.danq\.me|
                            tube\.darfweb\.eu|
                            tube\.darknight-coffee\.org|
                            tube\.dev\.lhub\.pl|
                            tube\.distrilab\.fr|
                            tube\.dodsorf\.as|
                            tube\.dragonpsi\.xyz|
                            tube\.dsocialize\.net|
                            tube\.ebin\.club|
                            tube\.egf\.mn|
                            tube\.eskuero\.me|
                            tube\.extinctionrebellion\.fr|
                            tube\.fab-l3\.org|
                            tube\.fabrigli\.fr|
                            tube\.fdn\.fr|
                            tube\.fede\.re|
                            tube\.florimond\.eu|
                            tube\.foxarmy\.ml|
                            tube\.foxden\.party|
                            tube\.frischesicht\.de|
                            tube\.futuretic\.fr|
                            tube\.gnous\.eu|
                            tube\.govital\.net|
                            tube\.grap\.coop|
                            tube\.graz\.social|
                            tube\.grin\.hu|
                            tube\.h3z\.jp|
                            tube\.hackerscop\.org|
                            tube\.hoga\.fr|
                            tube\.homecomputing\.fr|
                            tube\.hordearii\.fr|
                            tube\.ipfixe\.info|
                            tube\.jeena\.net|
                            tube\.kai-stuht\.com|
                            tube\.kalah-france\.org|
                            tube\.kampftoast\.de|
                            tube\.kdy\.ch|
                            tube\.kher\.nl|
                            tube\.kicou\.info|
                            tube\.kockatoo\.org|
                            tube\.kotur\.org|
                            tube\.ksl-bmx\.de|
                            tube\.lacaveatonton\.ovh|
                            tube\.linkse\.media|
                            tube\.lokad\.com|
                            tube\.lou\.lt|
                            tube\.lucie-philou\.com|
                            tube\.maiti\.info|
                            tube\.melonbread\.xyz|
                            tube\.metadocs\.cc|
                            tube\.mfraters\.net|
                            tube\.midov\.pl|
                            tube\.mochi\.academy|
                            tube\.motuhake\.xyz|
                            tube\.mrbesen\.de|
                            tube\.nah\.re|
                            tube\.nchoco\.net|
                            tube\.nemsia\.org|
                            tube\.netzspielplatz\.de|
                            tube\.novg\.net|
                            tube\.nox-rhea\.org|
                            tube\.nuagelibre\.fr|
                            tube\.nx-pod\.de|
                            tube\.nx12\.net|
                            tube\.octaplex\.net|
                            tube\.odat\.xyz|
                            tube\.oisux\.org|
                            tube\.open-plug\.eu|
                            tube\.openalgeria\.org|
                            tube\.opportunis\.me|
                            tube\.org\.il|
                            tube\.ortion\.xyz|
                            tube\.others\.social|
                            tube\.otter\.sh|
                            tube\.ouahpiti\.info|
                            tube\.p2p\.legal|
                            tube\.pasa\.tf|
                            tube\.pawelko\.net|
                            tube\.pericoloso\.ovh|
                            tube\.picasoft\.net|
                            tube\.piweb\.be|
                            tube\.plaf\.fr|
                            tube\.plomlompom\.com|
                            tube\.plus200\.com|
                            tube\.pmj\.rocks|
                            tube\.port0\.xyz|
                            tube\.portes-imaginaire\.org|
                            tube\.postblue\.info|
                            tube\.pyngu\.com|
                            tube\.rebellion\.global|
                            tube\.rfc1149\.net|
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
                            tube\.stanisic\.nl|
                            tube\.stbr\.io|
                            tube\.superseriousbusiness\.org|
                            tube\.svnet\.fr|
                            tube\.systest\.eu|
                            tube\.taker\.fr|
                            tube\.tappret\.fr|
                            tube\.tardis\.world|
                            tube\.tchncs\.de|
                            tube\.thechangebook\.org|
                            tube\.theocevaer\.fr|
                            tube\.toontoet\.nl|
                            tube\.tpshd\.de|
                            tube\.traydent\.info|
                            tube\.troopers\.agency|
                            tube\.tylerdavis\.xyz|
                            tube\.undernet\.uy|
                            tube\.unmondemeilleur\.eu|
                            tube\.valinor\.fr|
                            tube\.vigilian-consulting\.nl|
                            tube\.vraphim\.com|
                            tube\.wehost\.lgbt|
                            tube\.wien\.rocks|
                            tube\.wolfe\.casa|
                            tube\.worldofhauru\.xyz|
                            tube\.xd0\.de|
                            tube\.xy-space\.de|
                            tube\.yapbreak\.fr|
                            tubedu\.org|
                            tubee\.fr|
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
                            tv\.datamol\.org|
                            tv\.generallyrubbish\.net\.au|
                            tv\.lumbung\.space|
                            tv\.mattchristiansenmedia\.com|
                            tv\.mooh\.fr|
                            tv\.netwhood\.online|
                            tv\.neue\.city|
                            tv\.piejacker\.net|
                            tv\.pirateradio\.social|
                            tv\.undersco\.re|
                            tvox\.ru|
                            twctube\.twc-zone\.eu|
                            unfilter\.tube|
                            us\.tv|
                            v\.basspistol\.org|
                            v\.bearvideo\.win|
                            v\.kisombrella\.top|
                            v\.kretschmann\.social|
                            v\.lastorder\.xyz|
                            v\.lesterpig\.com|
                            v\.lor\.sh|
                            v\.mbius\.io|
                            v\.mom-gay\.faith|
                            v\.phreedom\.club|
                            v\.sil\.sh|
                            v\.szy\.io|
                            v\.xxxapex\.com|
                            vault\.mle\.party|
                            veezee\.tube|
                            vid\.dascoyote\.xyz|
                            vid\.garwood\.io|
                            vid\.lelux\.fi|
                            vid\.ncrypt\.at|
                            vid\.pravdastalina\.info|
                            vid\.qorg11\.net|
                            vid\.rajeshtaylor\.com|
                            vid\.samtripoli\.com|
                            vid\.werefox\.dev|
                            vid\.wildeboer\.net|
                            vid\.y-y\.li|
                            vidcommons\.org|
                            video-cave-v2\.de|
                            video\.076\.ne\.jp|
                            video\.1000i100\.fr|
                            video\.1146\.nohost\.me|
                            video\.alternanet\.fr|
                            video\.altertek\.org|
                            video\.amic37\.fr|
                            video\.anartist\.org|
                            video\.anormallostpod\.ovh|
                            video\.antirep\.net|
                            video\.antopie\.org|
                            video\.apps\.thedoodleproject\.net|
                            video\.arbitrarion\.com|
                            video\.artist\.cx|
                            video\.asgardius\.company|
                            video\.balsillie\.net|
                            video\.bards\.online|
                            video\.binarydad\.com|
                            video\.blast-info\.fr|
                            video\.blender\.org|
                            video\.blueline\.mg|
                            video\.bruitbruit\.com|
                            video\.cabane-libre\.org|
                            video\.catgirl\.biz|
                            video\.cigliola\.com|
                            video\.cm-en-transition\.fr|
                            video\.cnt\.social|
                            video\.coales\.co|
                            video\.codingfield\.com|
                            video\.colibris-outilslibres\.org|
                            video\.comptoir\.net|
                            video\.comune\.trento\.it|
                            video\.coop\.tools|
                            video\.cpn\.so|
                            video\.csc49\.fr|
                            video\.cybre\.town|
                            video\.datsemultimedia\.com|
                            video\.deadsuperhero\.com|
                            video\.demokratischer-sommer\.de|
                            video\.devinberg\.com|
                            video\.die-partei\.social|
                            video\.discord-insoumis\.fr|
                            video\.dolphincastle\.com|
                            video\.dresden\.network|
                            video\.ecole-89\.com|
                            video\.elgrillolibertario\.org|
                            video\.emergeheart\.info|
                            video\.eradicatinglove\.xyz|
                            video\.ethantheenigma\.me|
                            video\.exodus-privacy\.eu\.org|
                            video\.farci\.org|
                            video\.fbxl\.net|
                            video\.fdlibre\.eu|
                            video\.fhtagn\.org|
                            video\.fitchfamily\.org|
                            video\.freeradical\.zone|
                            video\.g3l\.org|
                            video\.greenmycity\.eu|
                            video\.gresille\.org|
                            video\.grosskopfgames\.de|
                            video\.guerredeclasse\.fr|
                            video\.gyt\.is|
                            video\.hackers\.town|
                            video\.halle-leaks\.de|
                            video\.hardlimit\.com|
                            video\.heromuster\.com|
                            video\.hooli\.co|
                            video\.ifuncle\.kr|
                            video\.igem\.org|
                            video\.internet-czas-dzialac\.pl|
                            video\.iphodase\.fr|
                            video\.irem\.univ-paris-diderot\.fr|
                            video\.islameye\.com|
                            video\.ivel\.fr|
                            video\.kicik\.fr|
                            video\.kuba-orlik\.name|
                            video\.kyushojitsu\.ca|
                            video\.lacaveatonton\.ovh|
                            video\.latavernedejohnjohn\.fr|
                            video\.lavolte\.net|
                            video\.lemediatv\.fr|
                            video\.lequerrec\.eu|
                            video\.lespoesiesdheloise\.fr|
                            video\.liberta\.vip|
                            video\.liege\.bike|
                            video\.linc\.systems|
                            video\.linux\.it|
                            video\.linuxtrent\.it|
                            video\.livecchi\.cloud|
                            video\.lokal\.social|
                            video\.lono\.space|
                            video\.lqdn\.fr|
                            video\.lunasqu\.ee|
                            video\.lundi\.am|
                            video\.lw1\.at|
                            video\.mantlepro\.com|
                            video\.marcorennmaus\.de|
                            video\.mass-trespass\.uk|
                            video\.migennes\.net|
                            video\.monarch-pass\.net|
                            video\.monsieur-a\.fr|
                            video\.monsieurbidouille\.fr|
                            video\.mstddntfdn\.online|
                            video\.mugoreve\.fr|
                            video\.mundodesconocido\.com|
                            video\.mycrowd\.ca|
                            video\.nesven\.eu|
                            video\.netsyms\.com|
                            video\.nogafam\.es|
                            video\.obermui\.de|
                            video\.odayacres\.farm|
                            video\.oh14\.de|
                            video\.okaris\.de|
                            video\.omniatv\.com|
                            video\.ozgurkon\.org|
                            video\.p1ng0ut\.social|
                            video\.p3x\.de|
                            video\.passageenseine\.fr|
                            video\.pcf\.fr|
                            video\.ploud\.fr|
                            video\.ploud\.jp|
                            video\.pony\.gallery|
                            video\.potate\.space|
                            video\.pourpenser\.pro|
                            video\.progressiv\.dev|
                            video\.qoto\.org|
                            video\.rastapuls\.com|
                            video\.resolutions\.it|
                            video\.rw501\.de|
                            video\.samedi\.pm|
                            video\.screamer\.wiki|
                            video\.sdm-tools\.net|
                            video\.selea\.se|
                            video\.sftblw\.moe|
                            video\.shitposter\.club|
                            video\.skyn3t\.in|
                            video\.soi\.ch|
                            video\.stuartbrand\.co\.uk|
                            video\.subak\.ovh|
                            video\.taboulisme\.com|
                            video\.tedomum\.net|
                            video\.thedwyers\.co|
                            video\.thinkof\.name|
                            video\.toot\.pt|
                            video\.triplea\.fr|
                            video\.turbo\.chat|
                            video\.typica\.us|
                            video\.up\.edu\.ph|
                            video\.vaku\.org\.ua|
                            video\.valme\.io|
                            video\.veloma\.org|
                            video\.violoncello\.ch|
                            video\.vny\.fr|
                            video\.wilkie\.how|
                            video\.writeas\.org|
                            video\.wsf2021\.info|
                            video\.yukari\.moe|
                            videobit\.cc|
                            videomensoif\.ynh\.fr|
                            videonaute\.fr|
                            videorelay\.co|
                            videos-libr\.es|
                            videos-passages\.huma-num\.fr|
                            videos\.3d-wolf\.com|
                            videos\.adhocmusic\.com|
                            videos\.ahp-numerique\.fr|
                            videos\.alexandrebadalo\.pt|
                            videos\.alolise\.org|
                            videos\.archigny\.net|
                            videos\.benjaminbrady\.ie|
                            videos\.benpro\.fr|
                            videos\.buceoluegoexisto\.com|
                            videos\.bugs\.social|
                            videos\.capas\.se|
                            videos\.casually\.cat|
                            videos\.cemea\.org|
                            videos\.cloudfrancois\.fr|
                            videos\.cloudron\.io|
                            videos\.coletivos\.org|
                            videos\.danksquad\.org|
                            videos\.darckoune\.moe|
                            videos\.denshi\.live|
                            videos\.dinofly\.com|
                            videos\.domainepublic\.net|
                            videos\.elbinario\.net|
                            videos\.festivalparminous\.org|
                            videos\.fromouter\.space|
                            videos\.fsci\.in|
                            videos\.funkwhale\.audio|
                            videos\.globenet\.org|
                            videos\.hack2g2\.fr|
                            videos\.hauspie\.fr|
                            videos\.hush\.is|
                            videos\.iut-orsay\.fr|
                            videos\.john-livingston\.fr|
                            videos\.jordanwarne\.xyz|
                            videos\.judrey\.eu|
                            videos\.koumoul\.com|
                            videos\.koweb\.fr|
                            videos\.lavoixdessansvoix\.org|
                            videos\.lescommuns\.org|
                            videos\.leslionsfloorball\.fr|
                            videos\.lucero\.top|
                            videos\.martyn\.berlin|
                            videos\.mastodont\.cat|
                            videos\.mleduc\.xyz|
                            videos\.monstro1\.com|
                            videos\.npo\.city|
                            videos\.numericoop\.fr|
                            videos\.numerique-en-commun\.fr|
                            videos\.optoutpod\.com|
                            videos\.pair2jeux\.tube|
                            videos\.petch\.rocks|
                            videos\.pofilo\.fr|
                            videos\.pueseso\.club|
                            videos\.pzelawski\.xyz|
                            videos\.rampin\.org|
                            videos\.scanlines\.xyz|
                            videos\.shmalls\.pw|
                            videos\.sibear\.fr|
                            videos\.side-ways\.net|
                            videos\.squat\.net|
                            videos\.stadtfabrikanten\.org|
                            videos\.tankernn\.eu|
                            videos\.tcit\.fr|
                            videos\.testimonia\.org|
                            videos\.thisishowidontdisappear\.com|
                            videos\.traumaheilung\.net|
                            videos\.trom\.tf|
                            videos\.ubuntu-paris\.org|
                            videos\.wakapo\.com|
                            videos\.wakkerewereld\.nu|
                            videos\.weblib\.re|
                            videos\.yesil\.club|
                            videosdulib\.re|
                            videotape\.me|
                            vids\.roshless\.me|
                            vids\.tekdmn\.me|
                            vidz\.dou\.bet|
                            vis\.ion\.ovh|
                            visionon\.tv|
                            vloggers\.social|
                            voca\.tube|
                            vod\.ksite\.de|
                            vod\.lumikko\.dev|
                            vod\.mochi\.academy|
                            vs\.uniter\.network|
                            vulgarisation-informatique\.fr|
                            watch\.44con\.com|
                            watch\.breadtube\.tv|
                            watch\.deranalyst\.ch|
                            watch\.ignorance\.eu|
                            watch\.krazy\.party|
                            watch\.libertaria\.space|
                            watch\.rt4mn\.org|
                            watch\.snoot\.tube|
                            watch\.softinio\.com|
                            watch\.tubelab\.video|
                            watching\.cypherpunk\.observer|
                            web-fellow\.de|
                            webtv\.vandoeuvre\.net|
                            wechill\.space|
                            widemus\.de|
                            wikileaks\.video|
                            wiwi\.video|
                            worldofvids\.com|
                            wwtube\.net|
                            www4\.mir\.inter21\.net|
                            www\.birkeundnymphe\.de|
                            www\.captain-german\.com|
                            www\.hkvideo\.live|
                            www\.videos-libr\.es|
                            www\.wiki-tube\.de|
                            www\.yiny\.org|
                            xxivproduction\.video|
                            xxx\.noho\.st|
                            yt\.is\.nota\.live|
                            yunopeertube\.myddns\.me
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
    _VALID_URL = r'''(?x)
                    (?:
                        https?://(?P<host>%s)/w/p/
                    )
                    (?P<id>%s)
                    ''' % (PeerTubeIE._INSTANCES_RE, PeerTubeIE._UUID_RE)
    _API_BASE = 'https://%s/api/v1/video-playlists/%s%s'
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
    }]
    _PAGE_SIZE = 30

    def _call_api(self, host, uuid, path, note=None, errnote=None, fatal=True):
        return self._download_json(
            self._API_BASE % (host, uuid, path), uuid,
            note=note, errnote=errnote, fatal=fatal)

    def _fetch_page(self, host, uuid, page):
        page += 1
        video_data = self._call_api(
            host, uuid, f'/videos?sort=-createdAt&start={self._PAGE_SIZE * (page - 1)}&count={self._PAGE_SIZE}',
            note=f'Downloading page {page}').get('data', [])
        for video in video_data:
            shortUUID = try_get(video, lambda x: x['video']['shortUUID'])
            video_title = try_get(video, lambda x: x['video']['name'])
            yield self.url_result(
                f'https://{host}/w/{shortUUID}', PeerTubeIE.ie_key(),
                video_id=shortUUID, video_title=video_title)

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        host = mobj.group('host')
        playlist_id = mobj.group('id')

        playlist_info = self._call_api(host, playlist_id, '', note='Downloading playlist information', fatal=False)

        playlist_title = playlist_info.get('displayName')
        playlist_description = playlist_info.get('description')
        playlist_timestamp = unified_timestamp(playlist_info.get('createdAt'))
        channel = try_get(playlist_info, lambda x: x['ownerAccount']['name'])
        channel_id = try_get(playlist_info, lambda x: x['ownerAccount']['id'])
        thumbnail = playlist_info.get('thumbnailPath')
        thumbnail = f'https://{host}{thumbnail}'

        entries = OnDemandPagedList(functools.partial(
            self._fetch_page, host, playlist_id), self._PAGE_SIZE)

        return self.playlist_result(
            entries, playlist_id, playlist_title, playlist_description,
            timestamp=playlist_timestamp, channel=channel, channel_id=channel_id, thumbnail=thumbnail)
