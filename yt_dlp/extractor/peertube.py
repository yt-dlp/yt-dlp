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
                            40two\.tube|
                            advtv\.ml|
                            algorithmic\.tv|
                            alimulama\.com|
                            alttube\.fr|
                            a\.metube\.ch|
                            aperi\.tube|
                            arcana\.fun|
                            archive\.vidicon\.org|
                            artefac-paris\.tv|
                            artitube\.artifaille\.fr|
                            auf1\.eu|
                            battlepenguin\.video|
                            beertube\.epgn\.ch|
                            befree\.nohost\.me|
                            bideoak\.argia\.eus|
                            birkeundnymphe\.de|
                            bitcointv\.com|
                            canard\.tube|
                            cattube\.org|
                            cinema\.yunohost\.support|
                            clap\.nerv-project\.eu|
                            climatejustice\.video|
                            comf\.tube|
                            conf\.tube|
                            conspiracydistillery\.com|
                            darkvapor\.nohost\.me|
                            daschauher\.aksel\.rocks|
                            devtube\.dev-wiki\.de|
                            dialup\.express|
                            digitalcourage\.video|
                            diode\.zone|
                            docker\.videos\.lecygnenoir\.info|
                            dreiecksnebel\.alex-detsch\.de|
                            eduvid\.org|
                            evangelisch\.video|
                            exode\.me|
                            exo\.tube|
                            fair\.tube|
                            fanvid\.stopthatimp\.net|
                            fediverse\.tv|
                            film\.k-prod\.fr|
                            film\.node9\.org|
                            flim\.txmn\.tk|
                            fontube\.fr|
                            fotogramas\.politicaconciencia\.org|
                            framatube\.org|
                            ftsi\.ru|
                            gary\.vger\.cloud|
                            graeber\.video|
                            greatview\.video|
                            grypstube\.uni-greifswald\.de|
                            highvoltage\.tv|
                            hitchtube\.fr|
                            hpstube\.fr|
                            htp\.live|
                            hyperreal\.tube|
                            indymotion\.fr|
                            irrsinn\.video|
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
                            livegram\.net|
                            live\.libratoi\.org|
                            live\.nanao\.moe|
                            live\.toobnix\.org|
                            lolitube\.freedomchan\.moe|
                            lostpod\.space|
                            lucarne\.balsamine\.be|
                            maindreieck-tv\.de|
                            manicphase\.me|
                            mani\.tube|
                            media\.assassinate-you\.net|
                            media\.gzevd\.de|
                            media\.inno3\.cricket|
                            media\.kaitaia\.life|
                            media\.krashboyz\.org|
                            media\.over-world\.org|
                            media\.privacyinternational\.org|
                            media\.skewed\.de|
                            medias\.pingbase\.net|
                            media\.undeadnetwork\.de|
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
                            offenes\.tv|
                            orgdup\.media|
                            ovaltube\.codinglab\.ch|
                            p2ptv\.ru|
                            peer\.azurs\.fr|
                            peer\.philoxweb\.be|
                            p\.eertu\.be|
                            peertube\.020\.pl|
                            peertube\.0x5e\.eu|
                            peertube\.1312\.media|
                            peertube1\.zeteo\.me|
                            peertube2\.cpy\.re|
                            peertube3\.cpy\.re|
                            peertube\.alpharius\.io|
                            peertube\.amicale\.net|
                            peertube\.am-networks\.fr|
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
                            peertube\.be|
                            peertube\.beeldengeluid\.nl|
                            peertube\.bgzashtita\.es|
                            peertube\.bilange\.ca|
                            peertube\.bitsandlinux\.com|
                            peertube\.biz|
                            peertube\.boba\.best|
                            peertube\.br0\.fr|
                            peertube\.bridaahost\.ynh\.fr|
                            peertube\.bubbletea\.dev|
                            peertube\.bubuit\.net|
                            peertube\.cabaal\.net|
                            peertube\.cats-home\.net|
                            peertube\.ch|
                            peertube\.chemnitz\.freifunk\.net|
                            peertube\.chevro\.fr|
                            peertube\.chrisspiegl\.com|
                            peertube\.chtisurel\.net|
                            peertube\.cipherbliss\.com|
                            peertube\.cloud\.sans\.pub|
                            peertube\.co\.uk|
                            peertube\.cpge-brizeux\.fr|
                            peertube\.cpy\.re|
                            peertube\.ctseuro\.com|
                            peertube\.cuatrolibertades\.org|
                            peertube\.cybercirujas\.club|
                            peertube\.cythin\.com|
                            peertube\.datagueule\.tv|
                            peertube\.davigge\.com|
                            peertube\.dc\.pini\.fr|
                            peertube\.debian\.social|
                            peertube\.demonix\.fr|
                            peertube\.designersethiques\.org|
                            peertube\.desmu\.fr|
                            peertube\.devloprog\.org|
                            peertube\.devol\.it|
                            peertube\.donnadieu\.fr|
                            peertube\.dtmf\.ca|
                            peertube\.dynlinux\.io|
                            peertube\.ecologie\.bzh|
                            peertube\.eu\.org|
                            peertube\.european-pirates\.eu|
                            peertube\.euskarabildua\.eus|
                            peertube\.fedi\.quebec|
                            peertube\.fenarinarsa\.com|
                            peertube\.ffs2play\.fr|
                            peertube\.floss-marketing-school\.com|
                            peertube\.fomin\.site|
                            peertube\.forsud\.be|
                            peertube\.fr|
                            peertube\.francoispelletier\.org|
                            peertube\.freeforge\.eu|
                            peertube\.freenet\.ru|
                            peertube\.freetalklive\.com|
                            peertube\.f-si\.org|
                            peertube\.functional\.cafe|
                            peertube\.gaialabs\.ch|
                            peertube\.gardeludwig\.fr|
                            peertube\.gargantia\.fr|
                            peertube\.gcfamily\.fr|
                            peertube\.gegeweb\.eu|
                            peertube\.genma\.fr|
                            peertube\.get-racing\.de|
                            peertube\.gidikroon\.eu|
                            peertube\.gruezishop\.ch|
                            peertube\.habets\.house|
                            peertube\.hackerfraternity\.org|
                            peertube\.heraut\.eu|
                            peertube\.ichigo\.everydayimshuflin\.com|
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
                            peertube\.kalua\.im|
                            peertube\.kathryl\.fr|
                            peertube\.keazilla\.net|
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
                            peertube\.lestutosdeprocessus\.fr|
                            peertube\.librenet\.co\.za|
                            peertube\.linuxrocks\.online|
                            peertube\.livingutopia\.org|
                            peertube\.logilab\.fr|
                            peertube\.louisematic\.site|
                            peertube\.luckow\.org|
                            peertube\.luga\.at|
                            peertube\.lyceeconnecte\.fr|
                            peertube\.makotoworkshop\.org|
                            peertube\.manalejandro\.com|
                            peertube\.marud\.fr|
                            peertube\.mattone\.net|
                            peertube\.maxweiss\.io|
                            peertube\.monlycee\.net|
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
                            peertube\.nz|
                            peertube\.offerman\.com|
                            peertube\.opencloud\.lu|
                            peertube\.openstreetmap\.fr|
                            peertube\.orthus\.link|
                            peertube\.patapouf\.xyz|
                            peertube\.pcservice46\.fr|
                            peertube\.pi2\.dev|
                            peertube\.pl|
                            peertube\.plataformess\.org|
                            peertube\.portaesgnos\.org|
                            peertube\.public\.cat|
                            peertube\.qtg\.fr|
                            peertube\.r2\.enst\.fr|
                            peertube\.r5c3\.fr|
                            peertube\.radres\.xyz|
                            peertube\.rainbowswingers\.net|
                            peertube\.red|
                            peertube\.robonomics\.network|
                            peertube\.roflcopter\.fr|
                            peertube\.rtnkv\.cloud|
                            peertube\.runfox\.tk|
                            peertube\.s2s\.video|
                            peertube\.satoshishop\.de|
                            peertube\.scic-tetris\.org|
                            peertube\.securitymadein\.lu|
                            peertube\.semweb\.pro|
                            peertube\.serveur\.slv-valbonne\.fr|
                            peertube\.simounet\.net|
                            peertube\.slat\.org|
                            peertube\.sl-network\.fr|
                            peertube\.snargol\.com|
                            peertube\.social|
                            peertube\.social\.my-wan\.de|
                            peertube\.solidev\.net|
                            peertube\.soykaf\.org|
                            peertube\.stefofficiel\.me|
                            peertube\.stemy\.me|
                            peertube\.stream|
                            peertube\.su|
                            peertube\.swarm\.solvingmaz\.es|
                            peertube\.swrs\.net|
                            peertube\.takeko\.cyou|
                            peertube\.tangentfox\.com|
                            peertube\.taxinachtegel\.de|
                            peertube\.thenewoil\.xyz|
                            peertube\.the-penguin\.de|
                            peertube\.tiennot\.net|
                            peertube\.ti-fr\.com|
                            peertube\.togart\.de|
                            peertube\.touhoppai\.moe|
                            peertube\.travelpandas\.eu|
                            peertube\.troback\.com|
                            peertube\.tspu\.edu\.ru|
                            peertube\.tux\.ovh|
                            peertube\.tv|
                            peertube\.tweb\.tv|
                            peertube\.ucy\.de|
                            peertube\.underworld\.fr|
                            peertube\.uno|
                            peertube\.us\.to|
                            peertube\.ventresmous\.fr|
                            peertube\.vlaki\.cz|
                            peertube\.we-keys\.fr|
                            peertube\.westring\.digital|
                            peertube\.w\.utnw\.de|
                            peertube\.xwiki\.com|
                            peertube\.zapashcanon\.fr|
                            peertube\.zergy\.net|
                            peertube\.zoz-serv\.org|
                            peervideo\.club|
                            peervideo\.ru|
                            periscope\.numenaute\.org|
                            perron-tube\.de|
                            petitlutinartube\.fr|
                            phijkchu\.com|
                            pierre\.tube|
                            piraten\.space|
                            pire\.artisanlogiciel\.net|
                            player\.ojamajo\.moe|
                            play\.rosano\.ca|
                            plextube\.nl|
                            p\.lu|
                            pocketnetpeertube1\.nohost\.me|
                            pocketnetpeertube3\.nohost\.me|
                            pocketnetpeertube4\.nohost\.me|
                            pocketnetpeertube5\.nohost\.me|
                            pocketnetpeertube6\.nohost\.me|
                            pt\.24-7\.ro|
                            pt\.apathy\.top|
                            ptb\.lunarviews\.net|
                            pt\.diaspodon\.fr|
                            pt\.fedi\.tech|
                            pt\.laurentkruger\.fr|
                            pt\.maciej\.website|
                            ptmir1\.inter21\.net|
                            ptmir2\.inter21\.net|
                            ptmir3\.inter21\.net|
                            ptmir4\.inter21\.net|
                            ptmir5\.inter21\.net|
                            ptube\.horsentiers\.fr|
                            ptube\.rousset\.nom\.fr|
                            ptube\.xmanifesto\.club|
                            queermotion\.org|
                            raptube\.antipub\.org|
                            refuznik\.video|
                            regarder\.sans\.pub|
                            repro\.video|
                            re-wizja\.re-medium\.com|
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
                            skeptikon\.fr|
                            sleepy\.tube|
                            sovran\.video|
                            spacepub\.space|
                            spectra\.video|
                            stream\.elven\.pw|
                            stream\.k-prod\.fr|
                            stream\.shahab\.nohost\.me|
                            streamsource\.video|
                            studios\.racer159\.com|
                            testtube\.florimond\.eu|
                            tgi\.hosted\.spacebear\.ee|
                            thaitube\.in\.th|
                            theater\.ethernia\.net|
                            thecool\.tube|
                            the\.jokertv\.eu|
                            thinkerview\.video|
                            tilvids\.com|
                            toob\.bub\.org|
                            toobnix\.org|
                            tpaw\.video|
                            troll\.tv|
                            truetube\.media|
                            tuba\.lhub\.pl|
                            tube1\.it\.tuwien\.ac\.at|
                            tube\.22decembre\.eu|
                            tube\.abolivier\.bzh|
                            tube\.ac-amiens\.fr|
                            tube\.ac-lyon\.fr|
                            tube\.aerztefueraufklaerung\.de|
                            tube-aix-marseille\.beta\.education\.fr|
                            tube\.alexx\.ml|
                            tube\.amic37\.fr|
                            tube-amiens\.beta\.education\.fr|
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
                            tube-besancon\.beta\.education\.fr|
                            tube\.bmesh\.org|
                            tube-bordeaux\.beta\.education\.fr|
                            tube\.borked\.host|
                            tube\.bruniau\.net|
                            tube\.bstly\.de|
                            tube\.calculate\.social|
                            tube\.chaoszone\.tv|
                            tube\.chatelet\.ovh|
                            tube-clermont-ferrand\.beta\.education\.fr|
                            tube\.cloud-libre\.eu|
                            tube\.cms\.garden|
                            tube\.conferences-gesticulees\.net|
                            tube-corse\.beta\.education\.fr|
                            tube\.cowfee\.moe|
                            tube\.crapaud-fou\.org|
                            tube-creteil\.beta\.education\.fr|
                            tube\.cryptography\.dog|
                            tube\.cyano\.at|
                            tube\.danq\.me|
                            tube\.darknight-coffee\.org|
                            tube\.dev\.lhub\.pl|
                            tube-dijon\.beta\.education\.fr|
                            tube\.distrilab\.fr|
                            tube\.dragonpsi\.xyz|
                            tube\.dsocialize\.net|
                            tubedu\.org|
                            tube\.ebin\.club|
                            tube-education\.beta\.education\.fr|
                            tube\.extinctionrebellion\.fr|
                            tube\.fdn\.fr|
                            tube\.fede\.re|
                            tube\.florimond\.eu|
                            tube\.foxarmy\.ml|
                            tube\.foxden\.party|
                            tube\.frischesicht\.de|
                            tube\.futuretic\.fr|
                            tube\.gnous\.eu|
                            tube\.grap\.coop|
                            tube\.graz\.social|
                            tube-grenoble\.beta\.education\.fr|
                            tube\.grin\.hu|
                            tube\.hackerscop\.org|
                            tube\.hoga\.fr|
                            tube\.homecomputing\.fr|
                            tube\.hordearii\.fr|
                            tube\.jeena\.net|
                            tube\.kai-stuht\.com|
                            tube\.kdy\.ch|
                            tube\.kicou\.info|
                            tube\.kockatoo\.org|
                            tube\.kotur\.org|
                            tube\.ksl-bmx\.de|
                            tube\.lacaveatonton\.ovh|
                            tube-lille\.beta\.education\.fr|
                            tube-limoges\.beta\.education\.fr|
                            tube\.linkse\.media|
                            tube\.lokad\.com|
                            tube\.lucie-philou\.com|
                            tube\.maiti\.info|
                            tube\.melonbread\.xyz|
                            tube\.mfraters\.net|
                            tube-montpellier\.beta\.education\.fr|
                            tube\.motuhake\.xyz|
                            tube\.mrbesen\.de|
                            tube\.nah\.re|
                            tube-nancy\.beta\.education\.fr|
                            tube-nantes\.beta\.education\.fr|
                            tube\.nchoco\.net|
                            tube-nice\.beta\.education\.fr|
                            tube-normandie\.beta\.education\.fr|
                            tube\.novg\.net|
                            tube\.nox-rhea\.org|
                            tube\.nuagelibre\.fr|
                            tube\.nx12\.net|
                            tube\.nx-pod\.de|
                            tube\.octaplex\.net|
                            tube\.odat\.xyz|
                            tube\.oisux\.org|
                            tube\.opportunis\.me|
                            tube\.org\.il|
                            tube-orleans-tours\.beta\.education\.fr|
                            tube\.ortion\.xyz|
                            tube\.others\.social|
                            tube-outremer\.beta\.education\.fr|
                            tube\.p2p\.legal|
                            tube-paris\.beta\.education\.fr|
                            tube\.picasoft\.net|
                            tube\.piweb\.be|
                            tube\.plaf\.fr|
                            tube\.plomlompom\.com|
                            tube\.pmj\.rocks|
                            tube-poitiers\.beta\.education\.fr|
                            tube\.port0\.xyz|
                            tube\.portes-imaginaire\.org|
                            tube\.postblue\.info|
                            tube\.pyngu\.com|
                            tube\.rebellion\.global|
                            tube-reims\.beta\.education\.fr|
                            tube-rennes\.beta\.education\.fr|
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
                            tubes\.jodh\.us|
                            tube\.skrep\.in|
                            tube\.sp4ke\.com|
                            tube\.sp-codes\.de|
                            tube-strasbourg\.beta\.education\.fr|
                            tube\.superseriousbusiness\.org|
                            tube\.systest\.eu|
                            tube\.taker\.fr|
                            tube\.tappret\.fr|
                            tube\.tardis\.world|
                            tube\.tchncs\.de|
                            tube\.thechangebook\.org|
                            tube\.toontoet\.nl|
                            tube-toulouse\.beta\.education\.fr|
                            tube\.tpshd\.de|
                            tube\.traydent\.info|
                            tube\.troopers\.agency|
                            tube\.tylerdavis\.xyz|
                            tube\.undernet\.uy|
                            tube\.valinor\.fr|
                            tube-versailles\.beta\.education\.fr|
                            tube\.vigilian-consulting\.nl|
                            tube\.vraphim\.com|
                            tube\.wehost\.lgbt|
                            tube\.wien\.rocks|
                            tube\.wolfe\.casa|
                            tube\.xd0\.de|
                            tube\.xy-space\.de|
                            tube\.yapbreak\.fr|
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
                            tvox\.ru|
                            tv\.piejacker\.net|
                            tv\.pirateradio\.social|
                            tv\.undersco\.re|
                            twctube\.twc-zone\.eu|
                            unfilter\.tube|
                            vault\.mle\.party|
                            v\.basspistol\.org|
                            veezee\.tube|
                            vidcommons\.org|
                            vid\.dascoyote\.xyz|
                            video\.076\.ne\.jp|
                            video\.1146\.nohost\.me|
                            video\.altertek\.org|
                            video\.anartist\.org|
                            video\.antopie\.org|
                            video\.apps\.thedoodleproject\.net|
                            video\.artist\.cx|
                            video\.asgardius\.company|
                            video\.balsillie\.net|
                            video\.bards\.online|
                            video\.binarydad\.com|
                            video\.blast-info\.fr|
                            video\.blender\.org|
                            video\.blueline\.mg|
                            video\.cabane-libre\.org|
                            video\.catgirl\.biz|
                            video-cave-v2\.de|
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
                            video\.demokratischer-sommer\.de|
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
                            video\.g3l\.org|
                            video\.greenmycity\.eu|
                            video\.guerredeclasse\.fr|
                            video\.gyt\.is|
                            video\.hackers\.town|
                            video\.hardlimit\.com|
                            video\.hooli\.co|
                            video\.igem\.org|
                            video\.internet-czas-dzialac\.pl|
                            video\.iphodase\.fr|
                            video\.irem\.univ-paris-diderot\.fr|
                            video\.islameye\.com|
                            video\.kicik\.fr|
                            video\.kuba-orlik\.name|
                            video\.kyushojitsu\.ca|
                            video\.latavernedejohnjohn\.fr|
                            video\.lavolte\.net|
                            video\.lemediatv\.fr|
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
                            video\.monsieurbidouille\.fr|
                            video\.mstddntfdn\.online|
                            video\.mugoreve\.fr|
                            video\.mundodesconocido\.com|
                            video\.mycrowd\.ca|
                            video\.nesven\.eu|
                            video\.netsyms\.com|
                            video\.nogafam\.es|
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
                            videorelay\.co|
                            video\.resolutions\.it|
                            video\.rw501\.de|
                            videos\.3d-wolf\.com|
                            videos\.adhocmusic\.com|
                            videos\.ahp-numerique\.fr|
                            videos\.alexandrebadalo\.pt|
                            videos\.alolise\.org|
                            videos\.archigny\.net|
                            videos\.benjaminbrady\.ie|
                            videos\.buceoluegoexisto\.com|
                            videos\.capas\.se|
                            videos\.casually\.cat|
                            videos\.cemea\.org|
                            videos\.cloudron\.io|
                            videos\.coletivos\.org|
                            video\.screamer\.wiki|
                            videos\.danksquad\.org|
                            videos\.denshi\.live|
                            video\.sdm-tools\.net|
                            videos\.domainepublic\.net|
                            video\.selea\.se|
                            videos\.festivalparminous\.org|
                            videos\.fromouter\.space|
                            videos\.fsci\.in|
                            video\.sftblw\.moe|
                            videos\.funkwhale\.audio|
                            videos\.globenet\.org|
                            videos\.hauspie\.fr|
                            video\.shitposter\.club|
                            videos\.hush\.is|
                            videos\.iut-orsay\.fr|
                            videos\.john-livingston\.fr|
                            videos\.jordanwarne\.xyz|
                            videos\.judrey\.eu|
                            videos\.koumoul\.com|
                            videos\.koweb\.fr|
                            video\.skyn3t\.in|
                            videos\.lavoixdessansvoix\.org|
                            videos\.lescommuns\.org|
                            videos\.leslionsfloorball\.fr|
                            videos\.lucero\.top|
                            videos\.martyn\.berlin|
                            videos\.mastodont\.cat|
                            videos\.monstro1\.com|
                            videos\.npo\.city|
                            video\.soi\.ch|
                            videos\.optoutpod\.com|
                            videos\.pair2jeux\.tube|
                            videos-passages\.huma-num\.fr|
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
                            video\.stuartbrand\.co\.uk|
                            video\.subak\.ovh|
                            videos\.ubuntu-paris\.org|
                            videos\.wakkerewereld\.nu|
                            videos\.weblib\.re|
                            videos\.yesil\.club|
                            video\.taboulisme\.com|
                            videotape\.me|
                            video\.tedomum\.net|
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
                            vid\.garwood\.io|
                            vid\.lelux\.fi|
                            vid\.ncrypt\.at|
                            vid\.pravdastalina\.info|
                            vid\.qorg11\.net|
                            vid\.rajeshtaylor\.com|
                            vid\.samtripoli\.com|
                            vids\.roshless\.me|
                            vids\.tekdmn\.me|
                            vid\.werefox\.dev|
                            vid\.wildeboer\.net|
                            vid\.y-y\.li|
                            vidz\.dou\.bet|
                            visionon\.tv|
                            v\.kisombrella\.top|
                            v\.kretschmann\.social|
                            v\.lastorder\.xyz|
                            v\.lesterpig\.com|
                            v\.lor\.sh|
                            vod\.ksite\.de|
                            vod\.lumikko\.dev|
                            v\.phreedom\.club|
                            v\.sil\.sh|
                            vs\.uniter\.network|
                            v\.szy\.io|
                            vulgarisation-informatique\.fr|
                            v\.xxxapex\.com|
                            watch\.44con\.com|
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
                            widemus\.de|
                            wikileaks\.video|
                            wiwi\.video|
                            worldofvids\.com|
                            wwtube\.net|
                            www4\.mir\.inter21\.net|
                            www\.birkeundnymphe\.de|
                            www\.captain-german\.com|
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
        'url': 'https://peertube.tamanoir.foucry.net/videos/watch/0b04f13d-1e18-4f1d-814e-4979aa7c9c44',
        'only_matching': True,
    }, {
        # nsfw
        'url': 'https://tube.22decembre.eu/videos/watch/9bb88cd3-9959-46d9-9ab9-33d2bb704c39',
        'only_matching': True,
    }, {
        'url': 'https://tube.22decembre.eu/videos/embed/fed67262-6edb-4d1c-833b-daa9085c71d7',
        'only_matching': True,
    }, {
        'url': 'https://tube.openalgeria.org/api/v1/videos/c1875674-97d0-4c94-a058-3f7e64c962e8',
        'only_matching': True,
    }, {
        'url': 'peertube:video.blender.org:b37a5b9f-e6b5-415c-b700-04a5cd6ec205',
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
                        peertube:(?P<host>[^:]+):|
                        https?://(?P<host_2>%s)/w/p/
                    )
                    (?P<id>%s)
                    ''' % (PeerTubeIE._INSTANCES_RE, PeerTubeIE._UUID_RE)
    _API_BASE = 'https://%s/api/v1/video-playlists/%s/videos'
    _TESTS = [{
        'url': 'https://peertube.tux.ovh/w/p/3af94cba-95e8-4b74-b37a-807ab6d82526',
        'info_dict': {
            'id': '3af94cba-95e8-4b74-b37a-807ab6d82526',
        },
        'playlist_mincount': 6,
    }, {
        'url': 'https://peertube.tux.ovh/w/p/wkyqcQBnsvFxtUB2pkYc1e',
        'info_dict': {
            'id': 'wkyqcQBnsvFxtUB2pkYc1e',
        },
        'playlist_mincount': 6,
    }]
    _PAGE_SIZE = 100

    def _call_api(self, host, playlist_uuid, note=None, errnote=None, fatal=True):
        return self._download_json(
            self._API_BASE % (host, playlist_uuid), playlist_uuid,
            note=note, errnote=errnote, fatal=fatal)

    def _fetch_page(self, host, uuid, page):
        page += 1
        video_data = self._call_api(host, uuid, f'Downloading {page} page').get('data', [])
        for video in video_data:
            shortUUID = try_get(video, lambda x: x['video']['shortUUID'])
            video_title = try_get(video, lambda x: x['video']['name'])
            yield self.url_result(
                f'https://{host}/w/{shortUUID}', PeerTubeIE.ie_key(),
                video_id=shortUUID, video_title=video_title)

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        host = mobj.group('host') or mobj.group('host_2')
        playlist_id = mobj.group('id')

        entries = OnDemandPagedList(functools.partial(
            self._fetch_page, host, playlist_id), self._PAGE_SIZE)

        return self.playlist_result(entries, playlist_id)
