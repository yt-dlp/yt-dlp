import functools
import re

from .common import InfoExtractor
from ..utils import (
    OnDemandPagedList,
    format_field,
    int_or_none,
    parse_resolution,
    str_or_none,
    try_get,
    unified_timestamp,
    url_or_none,
    urljoin,
)


class PeerTubeIE(InfoExtractor):
    _INSTANCES_RE = r'''(?:
                            # Taken from https://instances.joinpeertube.org/instances
                            0ch\.tv|
                            3dctube\.3dcandy\.social|
                            all\.electric\.kitchen|
                            alterscope\.fr|
                            anarchy\.tube|
                            apathy\.tv|
                            apertatube\.net|
                            archive\.nocopyrightintended\.tv|
                            archive\.reclaim\.tv|
                            area51\.media|
                            astrotube-ufe\.obspm\.fr|
                            astrotube\.obspm\.fr|
                            audio\.freediverse\.com|
                            azxtube\.youssefc\.tn|
                            bark\.video|
                            battlepenguin\.video|
                            bava\.tv|
                            bee-tube\.fr|
                            beetoons\.tv|
                            biblion\.refchat\.net|
                            biblioteca\.theowlclub\.net|
                            bideoak\.argia\.eus|
                            bideoteka\.eus|
                            birdtu\.be|
                            bitcointv\.com|
                            bonn\.video|
                            breeze\.tube|
                            brioco\.live|
                            brocosoup\.fr|
                            canal\.facil\.services|
                            canard\.tube|
                            cdn01\.tilvids\.com|
                            celluloid-media\.huma-num\.fr|
                            chicago1\.peertube\.support|
                            cliptube\.org|
                            cloudtube\.ise\.fraunhofer\.de|
                            comf\.tube|
                            comics\.peertube\.biz|
                            commons\.tube|
                            communitymedia\.video|
                            conspiracydistillery\.com|
                            crank\.recoil\.org|
                            dalek\.zone|
                            dalliance\.network|
                            dangly\.parts|
                            darkvapor\.nohost\.me|
                            daschauher\.aksel\.rocks|
                            digitalcourage\.video|
                            displayeurope\.video|
                            ds106\.tv|
                            dud-video\.inf\.tu-dresden\.de|
                            dud175\.inf\.tu-dresden\.de|
                            dytube\.com|
                            ebildungslabor\.video|
                            evangelisch\.video|
                            fair\.tube|
                            fedi\.video|
                            fedimovie\.com|
                            fediverse\.tv|
                            film\.k-prod\.fr|
                            flipboard\.video|
                            foss\.video|
                            fossfarmers\.company|
                            fotogramas\.politicaconciencia\.org|
                            freediverse\.com|
                            freesoto-u2151\.vm\.elestio\.app|
                            freesoto\.tv|
                            garr\.tv|
                            greatview\.video|
                            grypstube\.uni-greifswald\.de|
                            habratube\.site|
                            ilbjach\.ru|
                            infothema\.net|
                            itvplus\.iiens\.net|
                            johnydeep\.net|
                            juggling\.digital|
                            jupiter\.tube|
                            kadras\.live|
                            kino\.kompot\.si|
                            kino\.schuerz\.at|
                            kinowolnosc\.pl|
                            kirche\.peertube-host\.de|
                            kiwi\.froggirl\.club|
                            kodcast\.com|
                            kolektiva\.media|
                            kpop\.22x22\.ru|
                            kumi\.tube|
                            la2\.peertube\.support|
                            la3\.peertube\.support|
                            la4\.peertube\.support|
                            lastbreach\.tv|
                            lawsplaining\.peertube\.biz|
                            leopard\.tube|
                            live\.codinglab\.ch|
                            live\.libratoi\.org|
                            live\.oldskool\.fi|
                            live\.solari\.com|
                            lucarne\.balsamine\.be|
                            luxtube\.lu|
                            makertube\.net|
                            media\.econoalchemist\.com|
                            media\.exo\.cat|
                            media\.fsfe\.org|
                            media\.gzevd\.de|
                            media\.interior\.edu\.uy|
                            media\.krashboyz\.org|
                            media\.mzhd\.de|
                            media\.smz-ma\.de|
                            media\.theplattform\.net|
                            media\.undeadnetwork\.de|
                            medias\.debrouillonet\.org|
                            medias\.pingbase\.net|
                            mediatube\.fermalo\.fr|
                            melsungen\.peertube-host\.de|
                            merci-la-police\.fr|
                            mindlyvideos\.com|
                            mirror\.peertube\.metalbanana\.net|
                            mirrored\.rocks|
                            mix\.video|
                            mountaintown\.video|
                            movies\.metricsmaster\.eu|
                            mtube\.mooo\.com|
                            mytube\.kn-cloud\.de|
                            mytube\.le5emeaxe\.fr|
                            mytube\.madzel\.de|
                            nadajemy\.com|
                            nanawel-peertube\.dyndns\.org|
                            neat\.tube|
                            nethack\.tv|
                            nicecrew\.tv|
                            nightshift\.minnix\.dev|
                            nolog\.media|
                            nyltube\.nylarea\.com|
                            ocfedtest\.hosted\.spacebear\.ee|
                            openmedia\.edunova\.it|
                            p2ptv\.ru|
                            p\.eertu\.be|
                            p\.lu|
                            pastafriday\.club|
                            patriottube\.sonsofliberty\.red|
                            pcbu\.nl|
                            peer\.azurs\.fr|
                            peer\.d0g4\.me|
                            peer\.lukeog\.com|
                            peer\.madiator\.cloud|
                            peer\.raise-uav\.com|
                            peershare\.togart\.de|
                            peertube-blablalinux\.be|
                            peertube-demo\.learning-hub\.fr|
                            peertube-docker\.cpy\.re|
                            peertube-eu\.howlround\.com|
                            peertube-u5014\.vm\.elestio\.app|
                            peertube-us\.howlround\.com|
                            peertube\.020\.pl|
                            peertube\.0x5e\.eu|
                            peertube\.1984\.cz|
                            peertube\.2i2l\.net|
                            peertube\.adjutor\.xyz|
                            peertube\.adresse\.data\.gouv\.fr|
                            peertube\.alpharius\.io|
                            peertube\.am-networks\.fr|
                            peertube\.anduin\.net|
                            peertube\.anti-logic\.com|
                            peertube\.arch-linux\.cz|
                            peertube\.art3mis\.de|
                            peertube\.artsrn\.ualberta\.ca|
                            peertube\.askan\.info|
                            peertube\.astral0pitek\.synology\.me|
                            peertube\.atsuchan\.page|
                            peertube\.automat\.click|
                            peertube\.b38\.rural-it\.org|
                            peertube\.be|
                            peertube\.beeldengeluid\.nl|
                            peertube\.bgzashtita\.es|
                            peertube\.bike|
                            peertube\.bildung-ekhn\.de|
                            peertube\.biz|
                            peertube\.br0\.fr|
                            peertube\.bridaahost\.ynh\.fr|
                            peertube\.bubbletea\.dev|
                            peertube\.bubuit\.net|
                            peertube\.cabaal\.net|
                            peertube\.chatinbit\.com|
                            peertube\.chaunchy\.com|
                            peertube\.chir\.rs|
                            peertube\.christianpacaud\.com|
                            peertube\.chtisurel\.net|
                            peertube\.chuggybumba\.com|
                            peertube\.cipherbliss\.com|
                            peertube\.cirkau\.art|
                            peertube\.cloud\.nerdraum\.de|
                            peertube\.cloud\.sans\.pub|
                            peertube\.coko\.foundation|
                            peertube\.communecter\.org|
                            peertube\.concordia\.social|
                            peertube\.corrigan\.xyz|
                            peertube\.cpge-brizeux\.fr|
                            peertube\.ctseuro\.com|
                            peertube\.cuatrolibertades\.org|
                            peertube\.cube4fun\.net|
                            peertube\.dair-institute\.org|
                            peertube\.davigge\.com|
                            peertube\.dc\.pini\.fr|
                            peertube\.deadtom\.me|
                            peertube\.debian\.social|
                            peertube\.delta0189\.xyz|
                            peertube\.demonix\.fr|
                            peertube\.designersethiques\.org|
                            peertube\.desmu\.fr|
                            peertube\.devol\.it|
                            peertube\.dk|
                            peertube\.doesstuff\.social|
                            peertube\.eb8\.org|
                            peertube\.education-forum\.com|
                            peertube\.elforcer\.ru|
                            peertube\.em\.id\.lv|
                            peertube\.ethibox\.fr|
                            peertube\.eu\.org|
                            peertube\.european-pirates\.eu|
                            peertube\.eus|
                            peertube\.euskarabildua\.eus|
                            peertube\.expi\.studio|
                            peertube\.familie-berner\.de|
                            peertube\.familleboisteau\.fr|
                            peertube\.fedihost\.website|
                            peertube\.fenarinarsa\.com|
                            peertube\.festnoz\.de|
                            peertube\.forteza\.fr|
                            peertube\.freestorm\.online|
                            peertube\.functional\.cafe|
                            peertube\.gaminglinux\.fr|
                            peertube\.gargantia\.fr|
                            peertube\.geekgalaxy\.fr|
                            peertube\.gemlog\.ca|
                            peertube\.genma\.fr|
                            peertube\.get-racing\.de|
                            peertube\.ghis94\.ovh|
                            peertube\.gidikroon\.eu|
                            peertube\.giftedmc\.com|
                            peertube\.grosist\.fr|
                            peertube\.gruntwerk\.org|
                            peertube\.gsugambit\.com|
                            peertube\.hackerfoo\.com|
                            peertube\.hellsite\.net|
                            peertube\.helvetet\.eu|
                            peertube\.histoirescrepues\.fr|
                            peertube\.home\.x0r\.fr|
                            peertube\.hyperfreedom\.org|
                            peertube\.ichigo\.everydayimshuflin\.com|
                            peertube\.ifwo\.eu|
                            peertube\.in\.ua|
                            peertube\.inapurna\.org|
                            peertube\.informaction\.info|
                            peertube\.interhop\.org|
                            peertube\.it|
                            peertube\.it-arts\.net|
                            peertube\.jensdiemer\.de|
                            peertube\.johntheserg\.al|
                            peertube\.kaleidos\.net|
                            peertube\.kalua\.im|
                            peertube\.kcore\.org|
                            peertube\.keazilla\.net|
                            peertube\.klaewyss\.fr|
                            peertube\.kleph\.eu|
                            peertube\.kodein\.be|
                            peertube\.kooperatywa\.tech|
                            peertube\.kriom\.net|
                            peertube\.kx\.studio|
                            peertube\.kyriog\.eu|
                            peertube\.la-famille-muller\.fr|
                            peertube\.labeuropereunion\.eu|
                            peertube\.lagvoid\.com|
                            peertube\.lhc\.net\.br|
                            peertube\.libresolutions\.network|
                            peertube\.libretic\.fr|
                            peertube\.librosphere\.fr|
                            peertube\.logilab\.fr|
                            peertube\.lon\.tv|
                            peertube\.louisematic\.site|
                            peertube\.luckow\.org|
                            peertube\.luga\.at|
                            peertube\.lyceeconnecte\.fr|
                            peertube\.madixam\.xyz|
                            peertube\.magicstone\.dev|
                            peertube\.marienschule\.de|
                            peertube\.marud\.fr|
                            peertube\.maxweiss\.io|
                            peertube\.miguelcr\.me|
                            peertube\.mikemestnik\.net|
                            peertube\.mobilsicher\.de|
                            peertube\.monlycee\.net|
                            peertube\.mxinfo\.fr|
                            peertube\.naln1\.ca|
                            peertube\.netzbegruenung\.de|
                            peertube\.nicolastissot\.fr|
                            peertube\.nogafam\.fr|
                            peertube\.normalgamingcommunity\.cz|
                            peertube\.nz|
                            peertube\.offerman\.com|
                            peertube\.ohioskates\.com|
                            peertube\.onionstorm\.net|
                            peertube\.opencloud\.lu|
                            peertube\.otakufarms\.com|
                            peertube\.paladyn\.org|
                            peertube\.pix-n-chill\.fr|
                            peertube\.r2\.enst\.fr|
                            peertube\.r5c3\.fr|
                            peertube\.redpill-insight\.com|
                            peertube\.researchinstitute\.at|
                            peertube\.revelin\.fr|
                            peertube\.rlp\.schule|
                            peertube\.rokugan\.fr|
                            peertube\.rougevertbleu\.tv|
                            peertube\.roundpond\.net|
                            peertube\.rural-it\.org|
                            peertube\.satoshishop\.de|
                            peertube\.scyldings\.com|
                            peertube\.securitymadein\.lu|
                            peertube\.semperpax\.com|
                            peertube\.semweb\.pro|
                            peertube\.sensin\.eu|
                            peertube\.sidh\.bzh|
                            peertube\.skorpil\.cz|
                            peertube\.smertrios\.com|
                            peertube\.sqweeb\.net|
                            peertube\.stattzeitung\.org|
                            peertube\.stream|
                            peertube\.su|
                            peertube\.swrs\.net|
                            peertube\.takeko\.cyou|
                            peertube\.taxinachtegel\.de|
                            peertube\.teftera\.com|
                            peertube\.teutronic-services\.de|
                            peertube\.ti-fr\.com|
                            peertube\.tiennot\.net|
                            peertube\.tmp\.rcp\.tf|
                            peertube\.tspu\.edu\.ru|
                            peertube\.tv|
                            peertube\.tweb\.tv|
                            peertube\.underworld\.fr|
                            peertube\.vapronva\.pw|
                            peertube\.veen\.world|
                            peertube\.vesdia\.eu|
                            peertube\.virtual-assembly\.org|
                            peertube\.viviers-fibre\.net|
                            peertube\.vlaki\.cz|
                            peertube\.wiesbaden\.social|
                            peertube\.wivodaim\.net|
                            peertube\.wtf|
                            peertube\.wtfayla\.net|
                            peertube\.xrcb\.cat|
                            peertube\.xwiki\.com|
                            peertube\.zd\.do|
                            peertube\.zetamc\.net|
                            peertube\.zmuuf\.org|
                            peertube\.zoz-serv\.org|
                            peertube\.zwindler\.fr|
                            peervideo\.ru|
                            periscope\.numenaute\.org|
                            pete\.warpnine\.de|
                            petitlutinartube\.fr|
                            phijkchu\.com|
                            phoenixproject\.group|
                            piraten\.space|
                            pirtube\.calut\.fr|
                            pityu\.flaki\.hu|
                            play\.mittdata\.se|
                            player\.ojamajo\.moe|
                            podlibre\.video|
                            portal\.digilab\.nfa\.cz|
                            private\.fedimovie\.com|
                            pt01\.lehrerfortbildung-bw\.de|
                            pt\.diaspodon\.fr|
                            pt\.freedomwolf\.cc|
                            pt\.gordons\.gen\.nz|
                            pt\.ilyamikcoder\.com|
                            pt\.irnok\.net|
                            pt\.mezzo\.moe|
                            pt\.na4\.eu|
                            pt\.netcraft\.ch|
                            pt\.rwx\.ch|
                            pt\.sfunk1x\.com|
                            pt\.thishorsie\.rocks|
                            pt\.vern\.cc|
                            ptb\.lunarviews\.net|
                            ptube\.de|
                            ptube\.ranranhome\.info|
                            puffy\.tube|
                            puppet\.zone|
                            qtube\.qlyoung\.net|
                            quantube\.win|
                            rankett\.net|
                            replay\.jres\.org|
                            review\.peertube\.biz|
                            sdmtube\.fr|
                            secure\.direct-live\.net|
                            secure\.scanovid\.com|
                            seka\.pona\.la|
                            serv3\.wiki-tube\.de|
                            skeptube\.fr|
                            social\.fedimovie\.com|
                            socpeertube\.ru|
                            sovran\.video|
                            special\.videovortex\.tv|
                            spectra\.video|
                            stl1988\.peertube-host\.de|
                            stream\.biovisata\.lt|
                            stream\.conesphere\.cloud|
                            stream\.elven\.pw|
                            stream\.jurnalfm\.md|
                            stream\.k-prod\.fr|
                            stream\.litera\.tools|
                            stream\.nuemedia\.se|
                            stream\.rlp-media\.de|
                            stream\.vrse\.be|
                            studios\.racer159\.com|
                            styxhexenhammer666\.com|
                            syrteplay\.obspm\.fr|
                            t\.0x0\.st|
                            tbh\.co-shaoghal\.net|
                            test-fab\.ynh\.fr|
                            testube\.distrilab\.fr|
                            tgi\.hosted\.spacebear\.ee|
                            theater\.ethernia\.net|
                            thecool\.tube|
                            thevideoverse\.com|
                            tilvids\.com|
                            tinkerbetter\.tube|
                            tinsley\.video|
                            trailers\.ddigest\.com|
                            tube-action-educative\.apps\.education\.fr|
                            tube-arts-lettres-sciences-humaines\.apps\.education\.fr|
                            tube-cycle-2\.apps\.education\.fr|
                            tube-cycle-3\.apps\.education\.fr|
                            tube-education-physique-et-sportive\.apps\.education\.fr|
                            tube-enseignement-professionnel\.apps\.education\.fr|
                            tube-institutionnel\.apps\.education\.fr|
                            tube-langues-vivantes\.apps\.education\.fr|
                            tube-maternelle\.apps\.education\.fr|
                            tube-numerique-educatif\.apps\.education\.fr|
                            tube-sciences-technologies\.apps\.education\.fr|
                            tube-test\.apps\.education\.fr|
                            tube1\.perron-service\.de|
                            tube\.9minuti\.it|
                            tube\.abolivier\.bzh|
                            tube\.alado\.space|
                            tube\.amic37\.fr|
                            tube\.area404\.cloud|
                            tube\.arthack\.nz|
                            tube\.asulia\.fr|
                            tube\.awkward\.company|
                            tube\.azbyka\.ru|
                            tube\.azkware\.net|
                            tube\.bartrip\.me\.uk|
                            tube\.belowtoxic\.media|
                            tube\.bingle\.plus|
                            tube\.bit-friends\.de|
                            tube\.bstly\.de|
                            tube\.chosto\.me|
                            tube\.cms\.garden|
                            tube\.communia\.org|
                            tube\.cyberia\.club|
                            tube\.cybershock\.life|
                            tube\.dembased\.xyz|
                            tube\.dev\.displ\.eu|
                            tube\.digitalesozialearbeit\.de|
                            tube\.distrilab\.fr|
                            tube\.doortofreedom\.org|
                            tube\.dsocialize\.net|
                            tube\.e-jeremy\.com|
                            tube\.ebin\.club|
                            tube\.elemac\.fr|
                            tube\.erzbistum-hamburg\.de|
                            tube\.exozy\.me|
                            tube\.fdn\.fr|
                            tube\.fedi\.quebec|
                            tube\.fediverse\.at|
                            tube\.felinn\.org|
                            tube\.flokinet\.is|
                            tube\.foad\.me\.uk|
                            tube\.freepeople\.fr|
                            tube\.friloux\.me|
                            tube\.froth\.zone|
                            tube\.fulda\.social|
                            tube\.futuretic\.fr|
                            tube\.g1zm0\.de|
                            tube\.g4rf\.net|
                            tube\.gaiac\.io|
                            tube\.geekyboo\.net|
                            tube\.genb\.de|
                            tube\.ghk-academy\.info|
                            tube\.gi-it\.de|
                            tube\.grap\.coop|
                            tube\.graz\.social|
                            tube\.grin\.hu|
                            tube\.hokai\.lol|
                            tube\.int5\.net|
                            tube\.interhacker\.space|
                            tube\.invisible\.ch|
                            tube\.io18\.top|
                            tube\.itsg\.host|
                            tube\.jeena\.net|
                            tube\.kh-berlin\.de|
                            tube\.kockatoo\.org|
                            tube\.kotur\.org|
                            tube\.koweb\.fr|
                            tube\.la-dina\.net|
                            tube\.lab\.nrw|
                            tube\.lacaveatonton\.ovh|
                            tube\.laurent-malys\.fr|
                            tube\.leetdreams\.ch|
                            tube\.linkse\.media|
                            tube\.lokad\.com|
                            tube\.lucie-philou\.com|
                            tube\.media-techport\.de|
                            tube\.morozoff\.pro|
                            tube\.neshweb\.net|
                            tube\.nestor\.coop|
                            tube\.network\.europa\.eu|
                            tube\.nicfab\.eu|
                            tube\.nieuwwestbrabant\.nl|
                            tube\.nogafa\.org|
                            tube\.novg\.net|
                            tube\.nox-rhea\.org|
                            tube\.nuagelibre\.fr|
                            tube\.numerique\.gouv\.fr|
                            tube\.nuxnik\.com|
                            tube\.nx12\.net|
                            tube\.octaplex\.net|
                            tube\.oisux\.org|
                            tube\.okcinfo\.news|
                            tube\.onlinekirche\.net|
                            tube\.opportunis\.me|
                            tube\.oraclefilms\.com|
                            tube\.org\.il|
                            tube\.pacapime\.ovh|
                            tube\.parinux\.org|
                            tube\.pastwind\.top|
                            tube\.picasoft\.net|
                            tube\.pilgerweg-21\.de|
                            tube\.pmj\.rocks|
                            tube\.pol\.social|
                            tube\.ponsonaille\.fr|
                            tube\.portes-imaginaire\.org|
                            tube\.public\.apolut\.net|
                            tube\.pustule\.org|
                            tube\.pyngu\.com|
                            tube\.querdenken-711\.de|
                            tube\.rebellion\.global|
                            tube\.reseau-canope\.fr|
                            tube\.rhythms-of-resistance\.org|
                            tube\.risedsky\.ovh|
                            tube\.rooty\.fr|
                            tube\.rsi\.cnr\.it|
                            tube\.ryne\.moe|
                            tube\.schleuss\.online|
                            tube\.schule\.social|
                            tube\.sekretaerbaer\.net|
                            tube\.shanti\.cafe|
                            tube\.shela\.nu|
                            tube\.skrep\.in|
                            tube\.sleeping\.town|
                            tube\.sp-codes\.de|
                            tube\.spdns\.org|
                            tube\.systerserver\.net|
                            tube\.systest\.eu|
                            tube\.tappret\.fr|
                            tube\.techeasy\.org|
                            tube\.thierrytalbert\.fr|
                            tube\.tinfoil-hat\.net|
                            tube\.toldi\.eu|
                            tube\.tpshd\.de|
                            tube\.trax\.im|
                            tube\.troopers\.agency|
                            tube\.ttk\.is|
                            tube\.tuxfriend\.fr|
                            tube\.tylerdavis\.xyz|
                            tube\.ullihome\.de|
                            tube\.ulne\.be|
                            tube\.undernet\.uy|
                            tube\.vrpnet\.org|
                            tube\.wolfe\.casa|
                            tube\.xd0\.de|
                            tube\.xn--baw-joa\.social|
                            tube\.xy-space\.de|
                            tube\.yapbreak\.fr|
                            tubedu\.org|
                            tubulus\.openlatin\.org|
                            turtleisland\.video|
                            tututu\.tube|
                            tv\.adast\.dk|
                            tv\.adn\.life|
                            tv\.arns\.lt|
                            tv\.atmx\.ca|
                            tv\.based\.quest|
                            tv\.farewellutopia\.com|
                            tv\.filmfreedom\.net|
                            tv\.gravitons\.org|
                            tv\.io\.seg\.br|
                            tv\.lumbung\.space|
                            tv\.pirateradio\.social|
                            tv\.pirati\.cz|
                            tv\.santic-zombie\.ru|
                            tv\.undersco\.re|
                            tv\.zonepl\.net|
                            tvox\.ru|
                            twctube\.twc-zone\.eu|
                            twobeek\.com|
                            urbanists\.video|
                            v\.9tail\.net|
                            v\.basspistol\.org|
                            v\.j4\.lc|
                            v\.kisombrella\.top|
                            v\.koa\.im|
                            v\.kyaru\.xyz|
                            v\.lor\.sh|
                            v\.mkp\.ca|
                            v\.posm\.gay|
                            v\.slaycer\.top|
                            veedeo\.org|
                            vhs\.absturztau\.be|
                            vid\.cthos\.dev|
                            vid\.kinuseka\.us|
                            vid\.mkp\.ca|
                            vid\.nocogabriel\.fr|
                            vid\.norbipeti\.eu|
                            vid\.northbound\.online|
                            vid\.ohboii\.de|
                            vid\.plantplotting\.co\.uk|
                            vid\.pretok\.tv|
                            vid\.prometheus\.systems|
                            vid\.soafen\.love|
                            vid\.twhtv\.club|
                            vid\.wildeboer\.net|
                            video-cave-v2\.de|
                            video-liberty\.com|
                            video\.076\.ne\.jp|
                            video\.1146\.nohost\.me|
                            video\.9wd\.eu|
                            video\.abraum\.de|
                            video\.ados\.accoord\.fr|
                            video\.amiga-ng\.org|
                            video\.anartist\.org|
                            video\.asgardius\.company|
                            video\.audiovisuel-participatif\.org|
                            video\.bards\.online|
                            video\.barkoczy\.social|
                            video\.benetou\.fr|
                            video\.beyondwatts\.social|
                            video\.bgeneric\.net|
                            video\.bilecik\.edu\.tr|
                            video\.blast-info\.fr|
                            video\.bmu\.cloud|
                            video\.catgirl\.biz|
                            video\.causa-arcana\.com|
                            video\.chasmcity\.net|
                            video\.chbmeyer\.de|
                            video\.cigliola\.com|
                            video\.citizen4\.eu|
                            video\.clumsy\.computer|
                            video\.cnnumerique\.fr|
                            video\.cnr\.it|
                            video\.cnt\.social|
                            video\.coales\.co|
                            video\.comune\.trento\.it|
                            video\.coyp\.us|
                            video\.csc49\.fr|
                            video\.davduf\.net|
                            video\.davejansen\.com|
                            video\.dlearning\.nl|
                            video\.dnfi\.no|
                            video\.dresden\.network|
                            video\.drgnz\.club|
                            video\.dudenas\.lt|
                            video\.eientei\.org|
                            video\.ellijaymakerspace\.org|
                            video\.emergeheart\.info|
                            video\.eradicatinglove\.xyz|
                            video\.everythingbagel\.me|
                            video\.extremelycorporate\.ca|
                            video\.fabiomanganiello\.com|
                            video\.fedi\.bzh|
                            video\.fhtagn\.org|
                            video\.firehawk-systems\.com|
                            video\.fox-romka\.ru|
                            video\.fuss\.bz\.it|
                            video\.glassbeadcollective\.org|
                            video\.graine-pdl\.org|
                            video\.gyt\.is|
                            video\.hainry\.fr|
                            video\.hardlimit\.com|
                            video\.hostux\.net|
                            video\.igem\.org|
                            video\.infojournal\.fr|
                            video\.internet-czas-dzialac\.pl|
                            video\.interru\.io|
                            video\.ipng\.ch|
                            video\.ironsysadmin\.com|
                            video\.islameye\.com|
                            video\.jacen\.moe|
                            video\.jadin\.me|
                            video\.jeffmcbride\.net|
                            video\.jigmedatse\.com|
                            video\.kuba-orlik\.name|
                            video\.lacalligramme\.fr|
                            video\.lanceurs-alerte\.fr|
                            video\.laotra\.red|
                            video\.lapineige\.fr|
                            video\.laraffinerie\.re|
                            video\.lavolte\.net|
                            video\.liberta\.vip|
                            video\.libreti\.net|
                            video\.licentia\.net|
                            video\.linc\.systems|
                            video\.linux\.it|
                            video\.linuxtrent\.it|
                            video\.liveitlive\.show|
                            video\.lono\.space|
                            video\.lrose\.de|
                            video\.lunago\.net|
                            video\.lundi\.am|
                            video\.lycee-experimental\.org|
                            video\.maechler\.cloud|
                            video\.marcorennmaus\.de|
                            video\.mass-trespass\.uk|
                            video\.matomocamp\.org|
                            video\.medienzentrum-harburg\.de|
                            video\.mentality\.rip|
                            video\.metaversum\.wtf|
                            video\.midreality\.com|
                            video\.mttv\.it|
                            video\.mugoreve\.fr|
                            video\.mxtthxw\.art|
                            video\.mycrowd\.ca|
                            video\.niboe\.info|
                            video\.nogafam\.es|
                            video\.nstr\.no|
                            video\.occm\.cc|
                            video\.off-investigation\.fr|
                            video\.olos311\.org|
                            video\.ordinobsolete\.fr|
                            video\.osvoj\.ru|
                            video\.ourcommon\.cloud|
                            video\.ozgurkon\.org|
                            video\.pcf\.fr|
                            video\.pcgaldo\.com|
                            video\.phyrone\.de|
                            video\.poul\.org|
                            video\.publicspaces\.net|
                            video\.pullopen\.xyz|
                            video\.r3s\.nrw|
                            video\.rainevixen\.com|
                            video\.resolutions\.it|
                            video\.retroedge\.tech|
                            video\.rhizome\.org|
                            video\.rlp-media\.de|
                            video\.rs-einrich\.de|
                            video\.rubdos\.be|
                            video\.sadmin\.io|
                            video\.sftblw\.moe|
                            video\.shitposter\.club|
                            video\.simplex-software\.ru|
                            video\.slipfox\.xyz|
                            video\.snug\.moe|
                            video\.software-fuer-engagierte\.de|
                            video\.soi\.ch|
                            video\.sonet\.ws|
                            video\.surazal\.net|
                            video\.taskcards\.eu|
                            video\.team-lcbs\.eu|
                            video\.techforgood\.social|
                            video\.telemillevaches\.net|
                            video\.thepolarbear\.co\.uk|
                            video\.thinkof\.name|
                            video\.tii\.space|
                            video\.tkz\.es|
                            video\.trankil\.info|
                            video\.triplea\.fr|
                            video\.tum\.social|
                            video\.turbo\.chat|
                            video\.uriopss-pdl\.fr|
                            video\.ustim\.ru|
                            video\.ut0pia\.org|
                            video\.vaku\.org\.ua|
                            video\.vegafjord\.me|
                            video\.veloma\.org|
                            video\.violoncello\.ch|
                            video\.voidconspiracy\.band|
                            video\.wakkeren\.nl|
                            video\.windfluechter\.org|
                            video\.ziez\.eu|
                            videos-passages\.huma-num\.fr|
                            videos\.aadtp\.be|
                            videos\.ahp-numerique\.fr|
                            videos\.alamaisondulibre\.org|
                            videos\.archigny\.net|
                            videos\.aroaduntraveled\.com|
                            videos\.b4tech\.org|
                            videos\.benjaminbrady\.ie|
                            videos\.bik\.opencloud\.lu|
                            videos\.cloudron\.io|
                            videos\.codingotaku\.com|
                            videos\.coletivos\.org|
                            videos\.collate\.social|
                            videos\.danksquad\.org|
                            videos\.digitaldragons\.eu|
                            videos\.dromeadhere\.fr|
                            videos\.explain-it\.org|
                            videos\.factsonthegroundshow\.com|
                            videos\.foilen\.com|
                            videos\.fsci\.in|
                            videos\.gamercast\.net|
                            videos\.gianmarco\.gg|
                            videos\.globenet\.org|
                            videos\.grafo\.zone|
                            videos\.hauspie\.fr|
                            videos\.hush\.is|
                            videos\.hyphalfusion\.network|
                            videos\.icum\.to|
                            videos\.im\.allmendenetz\.de|
                            videos\.jacksonchen666\.com|
                            videos\.john-livingston\.fr|
                            videos\.knazarov\.com|
                            videos\.kuoushi\.com|
                            videos\.laliguepaysdelaloire\.org|
                            videos\.lemouvementassociatif-pdl\.org|
                            videos\.leslionsfloorball\.fr|
                            videos\.librescrum\.org|
                            videos\.mastodont\.cat|
                            videos\.metus\.ca|
                            videos\.miolo\.org|
                            videos\.offroad\.town|
                            videos\.openmandriva\.org|
                            videos\.parleur\.net|
                            videos\.pcorp\.us|
                            videos\.pop\.eu\.com|
                            videos\.rampin\.org|
                            videos\.rauten\.co\.za|
                            videos\.ritimo\.org|
                            videos\.sarcasmstardust\.com|
                            videos\.scanlines\.xyz|
                            videos\.shmalls\.pw|
                            videos\.stadtfabrikanten\.org|
                            videos\.supertuxkart\.net|
                            videos\.testimonia\.org|
                            videos\.thinkerview\.com|
                            videos\.torrenezzi10\.xyz|
                            videos\.trom\.tf|
                            videos\.utsukta\.org|
                            videos\.viorsan\.com|
                            videos\.wherelinux\.xyz|
                            videos\.wikilibriste\.fr|
                            videos\.yesil\.club|
                            videos\.yeswiki\.net|
                            videotube\.duckdns\.org|
                            vids\.capypara\.de|
                            vids\.roshless\.me|
                            vids\.stary\.pc\.pl|
                            vids\.tekdmn\.me|
                            vidz\.julien\.ovh|
                            views\.southfox\.me|
                            virtual-girls-are\.definitely-for\.me|
                            viste\.pt|
                            vnchich\.com|
                            vnop\.org|
                            vod\.newellijay\.tv|
                            voluntarytube\.com|
                            vtr\.chikichiki\.tube|
                            vulgarisation-informatique\.fr|
                            watch\.easya\.solutions|
                            watch\.goodluckgabe\.life|
                            watch\.ignorance\.eu|
                            watch\.jimmydore\.com|
                            watch\.libertaria\.space|
                            watch\.nuked\.social|
                            watch\.ocaml\.org|
                            watch\.thelema\.social|
                            watch\.tubelab\.video|
                            web-fellow\.de|
                            webtv\.vandoeuvre\.net|
                            wetubevid\.online|
                            wikileaks\.video|
                            wiwi\.video|
                            wow\.such\.disappointment\.fail|
                            www\.jvideos\.net|
                            www\.kotikoff\.net|
                            www\.makertube\.net|
                            www\.mypeer\.tube|
                            www\.nadajemy\.com|
                            www\.neptube\.io|
                            www\.rocaguinarda\.tv|
                            www\.vnshow\.net|
                            xxivproduction\.video|
                            yt\.orokoro\.ru|
                            ytube\.retronerd\.at|
                            zumvideo\.de|

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
    _VALID_URL = rf'''(?x)
                    (?:
                        peertube:(?P<host>[^:]+):|
                        https?://(?P<host_2>{_INSTANCES_RE})/(?:videos/(?:watch|embed)|api/v\d/videos|w)/
                    )
                    (?P<id>{_UUID_RE})
                    '''
    _EMBED_REGEX = [r'''(?x)<iframe[^>]+\bsrc=["\'](?P<url>(?:https?:)?//{_INSTANCES_RE}/videos/embed/{cls._UUID_RE})''']
    _TESTS = [{
        'url': 'https://framatube.org/videos/watch/9c9de5e8-0a1e-484a-b099-e80766180a6d',
        'md5': '8563064d245a4be5705bddb22bb00a28',
        'info_dict': {
            'id': '9c9de5e8-0a1e-484a-b099-e80766180a6d',
            'ext': 'mp4',
            'title': 'What is PeerTube?',
            'description': 'md5:3fefb8dde2b189186ce0719fda6f7b10',
            'thumbnail': r're:https?://framatube\.org/lazy-static/thumbnails/.+\.jpg',
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
            'tags': 'count:2',
            'categories': ['Science & Technology'],
        },
        'expected_warnings': ['HTTP Error 400: Bad Request'],
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://peertube2.cpy.re/w/122d093a-1ede-43bd-bd34-59d2931ffc5e',
        'info_dict': {
            'id': '122d093a-1ede-43bd-bd34-59d2931ffc5e',
            'ext': 'mp4',
            'title': 'E2E tests',
            'categories': ['Unknown'],
            'channel': 'Main chocobozzz channel',
            'channel_id': '5187',
            'channel_url': 'https://peertube2.cpy.re/video-channels/chocobozzz_channel',
            'description': 'md5:67daf92c833c41c95db874e18fcb2786',
            'dislike_count': int,
            'duration': 52,
            'license': 'Unknown',
            'like_count': int,
            'tags': [],
            'thumbnail': r're:https?://peertube2\.cpy\.re/lazy-static/thumbnails/.+\.jpg',
            'timestamp': 1589276219,
            'upload_date': '20200512',
            'uploader': 'chocobozzz',
            'uploader_id': '37855',
            'uploader_url': 'https://peertube2.cpy.re/accounts/chocobozzz',
            'view_count': int,
        },
    }, {
        'url': 'https://peertube2.cpy.re/w/3fbif9S3WmtTP8gGsC5HBd',
        'info_dict': {
            'id': '3fbif9S3WmtTP8gGsC5HBd',
            'ext': 'mp4',
            'title': 'E2E tests',
            'categories': ['Unknown'],
            'channel': 'Main chocobozzz channel',
            'channel_id': '5187',
            'channel_url': 'https://peertube2.cpy.re/video-channels/chocobozzz_channel',
            'description': 'md5:67daf92c833c41c95db874e18fcb2786',
            'dislike_count': int,
            'duration': 52,
            'license': 'Unknown',
            'like_count': int,
            'tags': [],
            'thumbnail': r're:https?://peertube2\.cpy\.re/lazy-static/thumbnails/.+\.jpg',
            'timestamp': 1589276219,
            'upload_date': '20200512',
            'uploader': 'chocobozzz',
            'uploader_id': '37855',
            'uploader_url': 'https://peertube2.cpy.re/accounts/chocobozzz',
            'view_count': int,
        },
    }, {
        'url': 'https://peertube2.cpy.re/api/v1/videos/3fbif9S3WmtTP8gGsC5HBd',
        'info_dict': {
            'id': '3fbif9S3WmtTP8gGsC5HBd',
            'ext': 'mp4',
            'title': 'E2E tests',
            'categories': ['Unknown'],
            'channel': 'Main chocobozzz channel',
            'channel_id': '5187',
            'channel_url': 'https://peertube2.cpy.re/video-channels/chocobozzz_channel',
            'description': 'md5:67daf92c833c41c95db874e18fcb2786',
            'dislike_count': int,
            'duration': 52,
            'license': 'Unknown',
            'like_count': int,
            'tags': [],
            'thumbnail': r're:https?://peertube2\.cpy\.re/lazy-static/thumbnails/.+\.jpg',
            'timestamp': 1589276219,
            'upload_date': '20200512',
            'uploader': 'chocobozzz',
            'uploader_id': '37855',
            'uploader_url': 'https://peertube2.cpy.re/accounts/chocobozzz',
            'view_count': int,
        },
    }, {
        # https://github.com/ytdl-org/youtube-dl/issues/26002
        'url': 'peertube:spacepub.space:d8943b2d-8280-497b-85ec-bc282ec2afdc',
        'info_dict': {
            'id': 'd8943b2d-8280-497b-85ec-bc282ec2afdc',
            'ext': 'mp4',
            'title': 'Dot matrix printer shell demo',
            'uploader_id': '3',
            'timestamp': 1587401293,
            'upload_date': '20200420',
            'uploader': 'Drew DeVault',
        },
        'skip': 'Invalid URL',
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
    _WEBPAGE_TESTS = [{
        'url': 'https://video.macver.org/w/6gvhZpUGQVd4SQ6oYDc9pC',
        'info_dict': {
            'id': '6gvhZpUGQVd4SQ6oYDc9pC',
            'ext': 'mp4',
            'title': 'Minecraft, but if you say a block, it gets deleted',
            'categories': ['Gaming'],
            'channel': 'Waffle Irons Gaming',
            'channel_id': '4',
            'channel_url': 'https://video.macver.org/video-channels/waffle_irons',
            'description': 'md5:eda8daf64b0dadd00cc248f28eef213c',
            'dislike_count': int,
            'duration': 1643,
            'license': 'Attribution - Non Commercial',
            'like_count': int,
            'tags': 'count:1',
            'thumbnail': r're:https?://video\.macver\.org/lazy-static/thumbnails/.+\.jpg',
            'timestamp': 1751142352,
            'upload_date': '20250628',
            'uploader': 'Bog',
            'uploader_id': '3',
            'uploader_url': 'https://video.macver.org/accounts/bog',
            'view_count': int,
        },
        'expected_warnings': ['HTTP Error 400: Bad Request', 'Ignoring subtitle tracks found in the HLS manifest'],
        'params': {'skip_download': 'm3u8'},
    }]

    @staticmethod
    def _extract_peertube_url(webpage, source_url):
        mobj = re.match(
            rf'https?://(?P<host>[^/]+)/(?:videos/(?:watch|embed)|w)/(?P<id>{PeerTubeIE._UUID_RE})', source_url)
        if mobj and any(p in webpage for p in (
                'meta property="og:platform" content="PeerTube"',
                '<title>PeerTube<',
                'There will be other non JS-based clients to access PeerTube',
                '>We are sorry but it seems that PeerTube is not compatible with your web browser.<')):
            return 'peertube:{}:{}'.format(*mobj.group('host', 'id'))

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        embeds = tuple(super()._extract_embed_urls(url, webpage))
        if embeds:
            return embeds

        peertube_url = cls._extract_peertube_url(webpage, url)
        if peertube_url:
            return [peertube_url]

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
            language_id = try_get(e, lambda x: x['language']['id'], str)
            caption_url = urljoin(f'https://{host}', e.get('captionPath'))
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

        formats, is_live = [], False
        files = video.get('files') or []
        for playlist in (video.get('streamingPlaylists') or []):
            if not isinstance(playlist, dict):
                continue
            if playlist_url := url_or_none(playlist.get('playlistUrl')):
                is_live = True
                formats.extend(self._extract_m3u8_formats(
                    playlist_url, video_id, fatal=False, live=True))
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
                file_, lambda x: x['resolution']['label'], str)
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
            is_live = False
            formats.append(f)

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

        category = data('category', 'label', str)
        categories = [category] if category else None

        nsfw = video.get('nsfw')
        if nsfw is bool:
            age_limit = 18 if nsfw else 0
        else:
            age_limit = None

        webpage_url = f'https://{host}/videos/watch/{video_id}'

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': urljoin(webpage_url, video.get('thumbnailPath')),
            'timestamp': unified_timestamp(video.get('publishedAt')),
            'uploader': account_data('displayName', str),
            'uploader_id': str_or_none(account_data('id', int)),
            'uploader_url': url_or_none(account_data('url', str)),
            'channel': channel_data('displayName', str),
            'channel_id': str_or_none(channel_data('id', int)),
            'channel_url': url_or_none(channel_data('url', str)),
            'language': data('language', 'id', str),
            'license': data('licence', 'label', str),
            'duration': int_or_none(video.get('duration')),
            'view_count': int_or_none(video.get('views')),
            'like_count': int_or_none(video.get('likes')),
            'dislike_count': int_or_none(video.get('dislikes')),
            'age_limit': age_limit,
            'tags': try_get(video, lambda x: x['tags'], list),
            'categories': categories,
            'formats': formats,
            'subtitles': subtitles,
            'is_live': is_live,
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
                        https?://(?P<host>{})/(?P<type>(?:{}))/
                    (?P<id>[^/]+)
                    '''.format(PeerTubeIE._INSTANCES_RE, '|'.join(_TYPES.keys()))
    _TESTS = [{
        'url': 'https://peertube.debian.social/w/p/hFdJoTuyhNJVa1cDWd1d12',
        'info_dict': {
            'id': 'hFdJoTuyhNJVa1cDWd1d12',
            'description': 'Diversas palestras do Richard Stallman no Brasil.',
            'title': 'Richard Stallman no Brasil',
            'channel': 'debianbrazilteam',
            'channel_id': 1522,
            'thumbnail': r're:https?://peertube\.debian\.social/lazy-static/thumbnails/.+\.jpg',
            'timestamp': 1599676222,
            'upload_date': '20200909',
        },
        'playlist_mincount': 9,
    }, {
        'url': 'https://peertube2.cpy.re/a/chocobozzz/videos',
        'info_dict': {
            'id': 'chocobozzz',
            'title': 'chocobozzz',
            'channel': 'chocobozzz',
            'channel_id': 37855,
            'thumbnail': '',
            'timestamp': 1553874564,
            'upload_date': '20190329',
        },
        'playlist_mincount': 2,
    }, {
        'url': 'https://framatube.org/c/bf54d359-cfad-4935-9d45-9d6be93f63e8/videos',
        'info_dict': {
            'id': 'bf54d359-cfad-4935-9d45-9d6be93f63e8',
            'title': 'Les vidéos de Framasoft',
            'channel': 'framasoft',
            'channel_id': 3,
            'thumbnail': '',
            'timestamp': 1519917377,
            'upload_date': '20180301',
        },
        'playlist_mincount': 345,
    }, {
        'url': 'https://peertube2.cpy.re/c/blender_open_movies@video.blender.org/videos',
        'info_dict': {
            'id': 'blender_open_movies@video.blender.org',
            'title': 'Official Blender Open Movies',
            'channel': 'blender',
            'channel_id': 1926,
            'thumbnail': '',
            'timestamp': 1540472902,
            'upload_date': '20181025',
        },
        'playlist_mincount': 11,
    }]
    _API_BASE = 'https://%s/api/v1/%s/%s%s'
    _PAGE_SIZE = 30

    def call_api(self, host, name, path, base, **kwargs):
        return self._download_json(
            self._API_BASE % (host, base, name, path), name, **kwargs)

    def fetch_page(self, host, playlist_id, playlist_type, page):
        page += 1
        video_data = self.call_api(
            host, playlist_id,
            f'/videos?sort=-createdAt&start={self._PAGE_SIZE * (page - 1)}&count={self._PAGE_SIZE}&nsfw=both',
            playlist_type, note=f'Downloading page {page}').get('data', [])
        for video in video_data:
            short_uuid = video.get('shortUUID') or try_get(video, lambda x: x['video']['shortUUID'])
            video_title = video.get('name') or try_get(video, lambda x: x['video']['name'])
            yield self.url_result(
                f'https://{host}/w/{short_uuid}', PeerTubeIE.ie_key(),
                video_id=short_uuid, video_title=video_title)

    def _extract_playlist(self, host, playlist_type, playlist_id):
        info = self.call_api(host, playlist_id, '', playlist_type, note='Downloading playlist information', fatal=False)

        playlist_title = info.get('displayName')
        playlist_description = info.get('description')
        playlist_timestamp = unified_timestamp(info.get('createdAt'))
        channel = try_get(info, lambda x: x['ownerAccount']['name']) or info.get('displayName')
        channel_id = try_get(info, lambda x: x['ownerAccount']['id']) or info.get('id')
        thumbnail = format_field(info, 'thumbnailPath', f'https://{host}%s')

        entries = OnDemandPagedList(functools.partial(
            self.fetch_page, host, playlist_id, playlist_type), self._PAGE_SIZE)

        return self.playlist_result(
            entries, playlist_id, playlist_title, playlist_description,
            timestamp=playlist_timestamp, channel=channel, channel_id=channel_id, thumbnail=thumbnail)

    def _real_extract(self, url):
        playlist_type, host, playlist_id = self._match_valid_url(url).group('type', 'host', 'id')
        return self._extract_playlist(host, self._TYPES[playlist_type], playlist_id)
