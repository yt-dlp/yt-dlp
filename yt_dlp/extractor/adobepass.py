import getpass
import json
import re
import time
import urllib.parse
import xml.etree.ElementTree as etree

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    NO_DEFAULT,
    ExtractorError,
    unescapeHTML,
    unified_timestamp,
    urlencode_postdata,
)

MSO_INFO = {
    'DTV': {
        'name': 'DIRECTV',
        'username_field': 'username',
        'password_field': 'password',
    },
    'ATT': {
        'name': 'AT&T U-verse',
        'username_field': 'userid',
        'password_field': 'password',
    },
    'ATTOTT': {
        'name': 'DIRECTV NOW',
        'username_field': 'email',
        'password_field': 'loginpassword',
    },
    'RCN': {
        'name': 'RCN',
        'username_field': 'username',
        'password_field': 'password',
    },
    'Rogers': {
        'name': 'Rogers',
        'username_field': 'UserName',
        'password_field': 'UserPassword',
    },
    'Comcast_SSO': {
        'name': 'Comcast XFINITY',
        'username_field': 'user',
        'password_field': 'passwd',
    },
    'TWC': {
        'name': 'Time Warner Cable | Spectrum',
        'username_field': 'Ecom_User_ID',
        'password_field': 'Ecom_Password',
    },
    'Brighthouse': {
        'name': 'Bright House Networks | Spectrum',
        'username_field': 'j_username',
        'password_field': 'j_password',
    },
    'Charter_Direct': {
        'name': 'Charter Spectrum',
        'username_field': 'IDToken1',
        'password_field': 'IDToken2',
    },
    'Spectrum': {
        'name': 'Spectrum',
        'username_field': 'IDToken1',
        'password_field': 'IDToken2',
    },
    'Philo': {
        'name': 'Philo',
        'username_field': 'ident',
    },
    'Verizon': {
        'name': 'Verizon FiOS',
        'username_field': 'IDToken1',
        'password_field': 'IDToken2',
    },
    'Cablevision': {
        'name': 'Optimum/Cablevision',
        'username_field': 'j_username',
        'password_field': 'j_password',
    },
    'thr030': {
        'name': '3 Rivers Communications',
    },
    'com140': {
        'name': 'Access Montana',
    },
    'acecommunications': {
        'name': 'AcenTek',
    },
    'acm010': {
        'name': 'Acme Communications',
    },
    'ada020': {
        'name': 'Adams Cable Service',
    },
    'alb020': {
        'name': 'Albany Mutual Telephone',
    },
    'algona': {
        'name': 'Algona Municipal Utilities',
    },
    'allwest': {
        'name': 'All West Communications',
    },
    'all025': {
        'name': 'Allen\'s Communications',
    },
    'spl010': {
        'name': 'Alliance Communications',
    },
    'all070': {
        'name': 'ALLO Communications',
    },
    'alpine': {
        'name': 'Alpine Communications',
    },
    'hun015': {
        'name': 'American Broadband',
    },
    'nwc010': {
        'name': 'American Broadband Missouri',
    },
    'com130-02': {
        'name': 'American Community Networks',
    },
    'com130-01': {
        'name': 'American Warrior Networks',
    },
    'tom020': {
        'name': 'Amherst Telephone/Tomorrow Valley',
    },
    'tvc020': {
        'name': 'Andycable',
    },
    'arkwest': {
        'name': 'Arkwest Communications',
    },
    'art030': {
        'name': 'Arthur Mutual Telephone Company',
    },
    'arvig': {
        'name': 'Arvig',
    },
    'nttcash010': {
        'name': 'Ashland Home Net',
    },
    'astound': {
        'name': 'Astound (now Wave)',
    },
    'dix030': {
        'name': 'ATC Broadband',
    },
    'ara010': {
        'name': 'ATC Communications',
    },
    'she030-02': {
        'name': 'Ayersville Communications',
    },
    'baldwin': {
        'name': 'Baldwin Lightstream',
    },
    'bal040': {
        'name': 'Ballard TV',
    },
    'cit025': {
        'name': 'Bardstown Cable TV',
    },
    'bay030': {
        'name': 'Bay Country Communications',
    },
    'tel095': {
        'name': 'Beaver Creek Cooperative Telephone',
    },
    'bea020': {
        'name': 'Beaver Valley Cable',
    },
    'bee010': {
        'name': 'Bee Line Cable',
    },
    'wir030': {
        'name': 'Beehive Broadband',
    },
    'bra020': {
        'name': 'BELD',
    },
    'bel020': {
        'name': 'Bellevue Municipal Cable',
    },
    'vol040-01': {
        'name': 'Ben Lomand Connect / BLTV',
    },
    'bev010': {
        'name': 'BEVCOMM',
    },
    'big020': {
        'name': 'Big Sandy Broadband',
    },
    'ble020': {
        'name': 'Bledsoe Telephone Cooperative',
    },
    'bvt010': {
        'name': 'Blue Valley Tele-Communications',
    },
    'bra050': {
        'name': 'Brandenburg Telephone Co.',
    },
    'bte010': {
        'name': 'Bristol Tennessee Essential Services',
    },
    'annearundel': {
        'name': 'Broadstripe',
    },
    'btc010': {
        'name': 'BTC Communications',
    },
    'btc040': {
        'name': 'BTC Vision - Nahunta',
    },
    'bul010': {
        'name': 'Bulloch Telephone Cooperative',
    },
    'but010': {
        'name': 'Butler-Bremer Communications',
    },
    'tel160-csp': {
        'name': 'C Spire SNAP',
    },
    'csicable': {
        'name': 'Cable Services Inc.',
    },
    'cableamerica': {
        'name': 'CableAmerica',
    },
    'cab038': {
        'name': 'CableSouth Media 3',
    },
    'weh010-camtel': {
        'name': 'Cam-Tel Company',
    },
    'car030': {
        'name': 'Cameron Communications',
    },
    'canbytel': {
        'name': 'Canby Telcom',
    },
    'crt020': {
        'name': 'CapRock Tv',
    },
    'car050': {
        'name': 'Carnegie Cable',
    },
    'cas': {
        'name': 'CAS Cable',
    },
    'casscomm': {
        'name': 'CASSCOMM',
    },
    'mid180-02': {
        'name': 'Catalina Broadband Solutions',
    },
    'cccomm': {
        'name': 'CC Communications',
    },
    'nttccde010': {
        'name': 'CDE Lightband',
    },
    'cfunet': {
        'name': 'Cedar Falls Utilities',
    },
    'dem010-01': {
        'name': 'Celect-Bloomer Telephone Area',
    },
    'dem010-02': {
        'name': 'Celect-Bruce Telephone Area',
    },
    'dem010-03': {
        'name': 'Celect-Citizens Connected Area',
    },
    'dem010-04': {
        'name': 'Celect-Elmwood/Spring Valley Area',
    },
    'dem010-06': {
        'name': 'Celect-Mosaic Telecom',
    },
    'dem010-05': {
        'name': 'Celect-West WI Telephone Area',
    },
    'net010-02': {
        'name': 'Cellcom/Nsight Telservices',
    },
    'cen100': {
        'name': 'CentraCom',
    },
    'nttccst010': {
        'name': 'Central Scott / CSTV',
    },
    'cha035': {
        'name': 'Chaparral CableVision',
    },
    'cha050': {
        'name': 'Chariton Valley Communication Corporation, Inc.',
    },
    'cha060': {
        'name': 'Chatmoss Cablevision',
    },
    'nttcche010': {
        'name': 'Cherokee Communications',
    },
    'che050': {
        'name': 'Chesapeake Bay Communications',
    },
    'cimtel': {
        'name': 'Cim-Tel Cable, LLC.',
    },
    'cit180': {
        'name': 'Citizens Cablevision - Floyd, VA',
    },
    'cit210': {
        'name': 'Citizens Cablevision, Inc.',
    },
    'cit040': {
        'name': 'Citizens Fiber',
    },
    'cit250': {
        'name': 'Citizens Mutual',
    },
    'war040': {
        'name': 'Citizens Telephone Corporation',
    },
    'wat025': {
        'name': 'City Of Monroe',
    },
    'wadsworth': {
        'name': 'CityLink',
    },
    'nor100': {
        'name': 'CL Tel',
    },
    'cla010': {
        'name': 'Clarence Telephone and Cedar Communications',
    },
    'ser060': {
        'name': 'Clear Choice Communications',
    },
    'tac020': {
        'name': 'Click! Cable TV',
    },
    'war020': {
        'name': 'CLICK1.NET',
    },
    'cml010': {
        'name': 'CML Telephone Cooperative Association',
    },
    'cns': {
        'name': 'CNS',
    },
    'com160': {
        'name': 'Co-Mo Connect',
    },
    'coa020': {
        'name': 'Coast Communications',
    },
    'coa030': {
        'name': 'Coaxial Cable TV',
    },
    'mid055': {
        'name': 'Cobalt TV (Mid-State Community TV)',
    },
    'col070': {
        'name': 'Columbia Power & Water Systems',
    },
    'col080': {
        'name': 'Columbus Telephone',
    },
    'nor105': {
        'name': 'Communications 1 Cablevision, Inc.',
    },
    'com150': {
        'name': 'Community Cable & Broadband',
    },
    'com020': {
        'name': 'Community Communications Company',
    },
    'coy010': {
        'name': 'commZoom',
    },
    'com025': {
        'name': 'Complete Communication Services',
    },
    'cat020': {
        'name': 'Comporium',
    },
    'com071': {
        'name': 'ComSouth Telesys',
    },
    'consolidatedcable': {
        'name': 'Consolidated',
    },
    'conwaycorp': {
        'name': 'Conway Corporation',
    },
    'coo050': {
        'name': 'Coon Valley Telecommunications Inc',
    },
    'coo080': {
        'name': 'Cooperative Telephone Company',
    },
    'cpt010': {
        'name': 'CP-TEL',
    },
    'cra010': {
        'name': 'Craw-Kan Telephone',
    },
    'crestview': {
        'name': 'Crestview Cable Communications',
    },
    'cross': {
        'name': 'Cross TV',
    },
    'cro030': {
        'name': 'Crosslake Communications',
    },
    'ctc040': {
        'name': 'CTC - Brainerd MN',
    },
    'phe030': {
        'name': 'CTV-Beam - East Alabama',
    },
    'cun010': {
        'name': 'Cunningham Telephone & Cable',
    },
    'dpc010': {
        'name': 'D & P Communications',
    },
    'dak030': {
        'name': 'Dakota Central Telecommunications',
    },
    'nttcdel010': {
        'name': 'Delcambre Telephone LLC',
    },
    'tel160-del': {
        'name': 'Delta Telephone Company',
    },
    'sal040': {
        'name': 'DiamondNet',
    },
    'ind060-dc': {
        'name': 'Direct Communications',
    },
    'doy010': {
        'name': 'Doylestown Cable TV',
    },
    'dic010': {
        'name': 'DRN',
    },
    'dtc020': {
        'name': 'DTC',
    },
    'dtc010': {
        'name': 'DTC Cable (Delhi)',
    },
    'dum010': {
        'name': 'Dumont Telephone Company',
    },
    'dun010': {
        'name': 'Dunkerton Telephone Cooperative',
    },
    'cci010': {
        'name': 'Duo County Telecom',
    },
    'eagle': {
        'name': 'Eagle Communications',
    },
    'weh010-east': {
        'name': 'East Arkansas Cable TV',
    },
    'eatel': {
        'name': 'EATEL Video, LLC',
    },
    'ell010': {
        'name': 'ECTA',
    },
    'emerytelcom': {
        'name': 'Emery Telcom Video LLC',
    },
    'nor200': {
        'name': 'Empire Access',
    },
    'endeavor': {
        'name': 'Endeavor Communications',
    },
    'sun045': {
        'name': 'Enhanced Telecommunications Corporation',
    },
    'mid030': {
        'name': 'enTouch',
    },
    'epb020': {
        'name': 'EPB Smartnet',
    },
    'jea010': {
        'name': 'EPlus Broadband',
    },
    'com065': {
        'name': 'ETC',
    },
    'ete010': {
        'name': 'Etex Communications',
    },
    'fbc-tele': {
        'name': 'F&B Communications',
    },
    'fal010': {
        'name': 'Falcon Broadband',
    },
    'fam010': {
        'name': 'FamilyView CableVision',
    },
    'far020': {
        'name': 'Farmers Mutual Telephone Company',
    },
    'fay010': {
        'name': 'Fayetteville Public Utilities',
    },
    'sal060': {
        'name': 'fibrant',
    },
    'fid010': {
        'name': 'Fidelity Communications',
    },
    'for030': {
        'name': 'FJ Communications',
    },
    'fli020': {
        'name': 'Flint River Communications',
    },
    'far030': {
        'name': 'FMT - Jesup',
    },
    'foo010': {
        'name': 'Foothills Communications',
    },
    'for080': {
        'name': 'Forsyth CableNet',
    },
    'fbcomm': {
        'name': 'Frankfort Plant Board',
    },
    'tel160-fra': {
        'name': 'Franklin Telephone Company',
    },
    'nttcftc010': {
        'name': 'FTC',
    },
    'fullchannel': {
        'name': 'Full Channel, Inc.',
    },
    'gar040': {
        'name': 'Gardonville Cooperative Telephone Association',
    },
    'gbt010': {
        'name': 'GBT Communications, Inc.',
    },
    'tec010': {
        'name': 'Genuine Telecom',
    },
    'clr010': {
        'name': 'Giant Communications',
    },
    'gla010': {
        'name': 'Glasgow EPB',
    },
    'gle010': {
        'name': 'Glenwood Telecommunications',
    },
    'gra060': {
        'name': 'GLW Broadband Inc.',
    },
    'goldenwest': {
        'name': 'Golden West Cablevision',
    },
    'vis030': {
        'name': 'Grantsburg Telcom',
    },
    'gpcom': {
        'name': 'Great Plains Communications',
    },
    'gri010': {
        'name': 'Gridley Cable Inc',
    },
    'hbc010': {
        'name': 'H&B Cable Services',
    },
    'hae010': {
        'name': 'Haefele TV Inc.',
    },
    'htc010': {
        'name': 'Halstad Telephone Company',
    },
    'har005': {
        'name': 'Harlan Municipal Utilities',
    },
    'har020': {
        'name': 'Hart Communications',
    },
    'ced010': {
        'name': 'Hartelco TV',
    },
    'hea040': {
        'name': 'Heart of Iowa Communications Cooperative',
    },
    'htc020': {
        'name': 'Hickory Telephone Company',
    },
    'nttchig010': {
        'name': 'Highland Communication Services',
    },
    'hig030': {
        'name': 'Highland Media',
    },
    'spc010': {
        'name': 'Hilliary Communications',
    },
    'hin020': {
        'name': 'Hinton CATV Co.',
    },
    'hometel': {
        'name': 'HomeTel Entertainment, Inc.',
    },
    'hoodcanal': {
        'name': 'Hood Canal Communications',
    },
    'weh010-hope': {
        'name': 'Hope - Prescott Cable TV',
    },
    'horizoncable': {
        'name': 'Horizon Cable TV, Inc.',
    },
    'hor040': {
        'name': 'Horizon Chillicothe Telephone',
    },
    'htc030': {
        'name': 'HTC Communications Co. - IL',
    },
    'htccomm': {
        'name': 'HTC Communications, Inc. - IA',
    },
    'wal005': {
        'name': 'Huxley Communications',
    },
    'imon': {
        'name': 'ImOn Communications',
    },
    'ind040': {
        'name': 'Independence Telecommunications',
    },
    'rrc010': {
        'name': 'Inland Networks',
    },
    'stc020': {
        'name': 'Innovative Cable TV St Croix',
    },
    'car100': {
        'name': 'Innovative Cable TV St Thomas-St John',
    },
    'icc010': {
        'name': 'Inside Connect Cable',
    },
    'int100': {
        'name': 'Integra Telecom',
    },
    'int050': {
        'name': 'Interstate Telecommunications Coop',
    },
    'irv010': {
        'name': 'Irvine Cable',
    },
    'k2c010': {
        'name': 'K2 Communications',
    },
    'kal010': {
        'name': 'Kalida Telephone Company, Inc.',
    },
    'kal030': {
        'name': 'Kalona Cooperative Telephone Company',
    },
    'kmt010': {
        'name': 'KMTelecom',
    },
    'kpu010': {
        'name': 'KPU Telecommunications',
    },
    'kuh010': {
        'name': 'Kuhn Communications, Inc.',
    },
    'lak130': {
        'name': 'Lakeland Communications',
    },
    'lan010': {
        'name': 'Langco',
    },
    'lau020': {
        'name': 'Laurel Highland Total Communications, Inc.',
    },
    'leh010': {
        'name': 'Lehigh Valley Cooperative Telephone',
    },
    'bra010': {
        'name': 'Limestone Cable/Bracken Cable',
    },
    'loc020': {
        'name': 'LISCO',
    },
    'lit020': {
        'name': 'Litestream',
    },
    'tel140': {
        'name': 'LivCom',
    },
    'loc010': {
        'name': 'LocalTel Communications',
    },
    'weh010-longview': {
        'name': 'Longview - Kilgore Cable TV',
    },
    'lon030': {
        'name': 'Lonsdale Video Ventures, LLC',
    },
    'lns010': {
        'name': 'Lost Nation-Elwood Telephone Co.',
    },
    'nttclpc010': {
        'name': 'LPC Connect',
    },
    'lumos': {
        'name': 'Lumos Networks',
    },
    'madison': {
        'name': 'Madison Communications',
    },
    'mad030': {
        'name': 'Madison County Cable Inc.',
    },
    'nttcmah010': {
        'name': 'Mahaska Communication Group',
    },
    'mar010': {
        'name': 'Marne & Elk Horn Telephone Company',
    },
    'mcc040': {
        'name': 'McClure Telephone Co.',
    },
    'mctv': {
        'name': 'MCTV',
    },
    'merrimac': {
        'name': 'Merrimac Communications Ltd.',
    },
    'metronet': {
        'name': 'Metronet',
    },
    'mhtc': {
        'name': 'MHTC',
    },
    'midhudson': {
        'name': 'Mid-Hudson Cable',
    },
    'midrivers': {
        'name': 'Mid-Rivers Communications',
    },
    'mid045': {
        'name': 'Midstate Communications',
    },
    'mil080': {
        'name': 'Milford Communications',
    },
    'min030': {
        'name': 'MINET',
    },
    'nttcmin010': {
        'name': 'Minford TV',
    },
    'san040-02': {
        'name': 'Mitchell Telecom',
    },
    'mlg010': {
        'name': 'MLGC',
    },
    'mon060': {
        'name': 'Mon-Cre TVE',
    },
    'mou110': {
        'name': 'Mountain Telephone',
    },
    'mou050': {
        'name': 'Mountain Village Cable',
    },
    'mtacomm': {
        'name': 'MTA Communications, LLC',
    },
    'mtc010': {
        'name': 'MTC Cable',
    },
    'med040': {
        'name': 'MTC Technologies',
    },
    'man060': {
        'name': 'MTCC',
    },
    'mtc030': {
        'name': 'MTCO Communications',
    },
    'mul050': {
        'name': 'Mulberry Telecommunications',
    },
    'mur010': {
        'name': 'Murray Electric System',
    },
    'musfiber': {
        'name': 'MUS FiberNET',
    },
    'mpw': {
        'name': 'Muscatine Power & Water',
    },
    'nttcsli010': {
        'name': 'myEVTV.com',
    },
    'nor115': {
        'name': 'NCC',
    },
    'nor260': {
        'name': 'NDTC',
    },
    'nctc': {
        'name': 'Nebraska Central Telecom, Inc.',
    },
    'nel020': {
        'name': 'Nelsonville TV Cable',
    },
    'nem010': {
        'name': 'Nemont',
    },
    'new075': {
        'name': 'New Hope Telephone Cooperative',
    },
    'nor240': {
        'name': 'NICP',
    },
    'cic010': {
        'name': 'NineStar Connect',
    },
    'nktelco': {
        'name': 'NKTelco',
    },
    'nortex': {
        'name': 'Nortex Communications',
    },
    'nor140': {
        'name': 'North Central Telephone Cooperative',
    },
    'nor030': {
        'name': 'Northland Communications',
    },
    'nor075': {
        'name': 'Northwest Communications',
    },
    'nor125': {
        'name': 'Norwood Light Broadband',
    },
    'net010': {
        'name': 'Nsight Telservices',
    },
    'dur010': {
        'name': 'Ntec',
    },
    'nts010': {
        'name': 'NTS Communications',
    },
    'new045': {
        'name': 'NU-Telecom',
    },
    'nulink': {
        'name': 'NuLink',
    },
    'jam030': {
        'name': 'NVC',
    },
    'far035': {
        'name': 'OmniTel Communications',
    },
    'onesource': {
        'name': 'OneSource Communications',
    },
    'cit230': {
        'name': 'Opelika Power Services',
    },
    'daltonutilities': {
        'name': 'OptiLink',
    },
    'mid140': {
        'name': 'OPTURA',
    },
    'ote010': {
        'name': 'OTEC Communication Company',
    },
    'cci020': {
        'name': 'Packerland Broadband',
    },
    'pan010': {
        'name': 'Panora Telco/Guthrie Center Communications',
    },
    'otter': {
        'name': 'Park Region Telephone & Otter Tail Telcom',
    },
    'mid050': {
        'name': 'Partner Communications Cooperative',
    },
    'fib010': {
        'name': 'Pathway',
    },
    'paulbunyan': {
        'name': 'Paul Bunyan Communications',
    },
    'pem020': {
        'name': 'Pembroke Telephone Company',
    },
    'mck010': {
        'name': 'Peoples Rural Telephone Cooperative',
    },
    'pul010': {
        'name': 'PES Energize',
    },
    'phi010': {
        'name': 'Philippi Communications System',
    },
    'phonoscope': {
        'name': 'Phonoscope Cable',
    },
    'pin070': {
        'name': 'Pine Belt Communications, Inc.',
    },
    'weh010-pine': {
        'name': 'Pine Bluff Cable TV',
    },
    'pin060': {
        'name': 'Pineland Telephone Cooperative',
    },
    'cam010': {
        'name': 'Pinpoint Communications',
    },
    'pio060': {
        'name': 'Pioneer Broadband',
    },
    'pioncomm': {
        'name': 'Pioneer Communications',
    },
    'pioneer': {
        'name': 'Pioneer DTV',
    },
    'pla020': {
        'name': 'Plant TiftNet, Inc.',
    },
    'par010': {
        'name': 'PLWC',
    },
    'pro035': {
        'name': 'PMT',
    },
    'vik011': {
        'name': 'Polar Cablevision',
    },
    'pottawatomie': {
        'name': 'Pottawatomie Telephone Co.',
    },
    'premiercomm': {
        'name': 'Premier Communications',
    },
    'psc010': {
        'name': 'PSC',
    },
    'pan020': {
        'name': 'PTCI',
    },
    'qco010': {
        'name': 'QCOL',
    },
    'qua010': {
        'name': 'Quality Cablevision',
    },
    'rad010': {
        'name': 'Radcliffe Telephone Company',
    },
    'car040': {
        'name': 'Rainbow Communications',
    },
    'rai030': {
        'name': 'Rainier Connect',
    },
    'ral010': {
        'name': 'Ralls Technologies',
    },
    'rct010': {
        'name': 'RC Technologies',
    },
    'red040': {
        'name': 'Red River Communications',
    },
    'ree010': {
        'name': 'Reedsburg Utility Commission',
    },
    'mol010': {
        'name': 'Reliance Connects- Oregon',
    },
    'res020': {
        'name': 'Reserve Telecommunications',
    },
    'weh010-resort': {
        'name': 'Resort TV Cable',
    },
    'rld010': {
        'name': 'Richland Grant Telephone Cooperative, Inc.',
    },
    'riv030': {
        'name': 'River Valley Telecommunications Coop',
    },
    'rockportcable': {
        'name': 'Rock Port Cablevision',
    },
    'rsf010': {
        'name': 'RS Fiber',
    },
    'rtc': {
        'name': 'RTC Communication Corp',
    },
    'res040': {
        'name': 'RTC-Reservation Telephone Coop.',
    },
    'rte010': {
        'name': 'RTEC Communications',
    },
    'stc010': {
        'name': 'S&T',
    },
    'san020': {
        'name': 'San Bruno Cable TV',
    },
    'san040-01': {
        'name': 'Santel',
    },
    'sav010': {
        'name': 'SCI Broadband-Savage Communications Inc.',
    },
    'sco050': {
        'name': 'Scottsboro Electric Power Board',
    },
    'scr010': {
        'name': 'Scranton Telephone Company',
    },
    'selco': {
        'name': 'SELCO',
    },
    'she010': {
        'name': 'Shentel',
    },
    'she030': {
        'name': 'Sherwood Mutual Telephone Association, Inc.',
    },
    'ind060-ssc': {
        'name': 'Silver Star Communications',
    },
    'sjoberg': {
        'name': 'Sjoberg\'s Inc.',
    },
    'sou025': {
        'name': 'SKT',
    },
    'sky050': {
        'name': 'SkyBest TV',
    },
    'nttcsmi010': {
        'name': 'Smithville Communications',
    },
    'woo010': {
        'name': 'Solarus',
    },
    'sou075': {
        'name': 'South Central Rural Telephone Cooperative',
    },
    'sou065': {
        'name': 'South Holt Cablevision, Inc.',
    },
    'sou035': {
        'name': 'South Slope Cooperative Communications',
    },
    'spa020': {
        'name': 'Spanish Fork Community Network',
    },
    'spe010': {
        'name': 'Spencer Municipal Utilities',
    },
    'spi005': {
        'name': 'Spillway Communications, Inc.',
    },
    'srt010': {
        'name': 'SRT',
    },
    'cccsmc010': {
        'name': 'St. Maarten Cable TV',
    },
    'sta025': {
        'name': 'Star Communications',
    },
    'sco020': {
        'name': 'STE',
    },
    'uin010': {
        'name': 'STRATA Networks',
    },
    'sum010': {
        'name': 'Sumner Cable TV',
    },
    'pie010': {
        'name': 'Surry TV/PCSI TV',
    },
    'swa010': {
        'name': 'Swayzee Communications',
    },
    'sweetwater': {
        'name': 'Sweetwater Cable Television Co',
    },
    'weh010-talequah': {
        'name': 'Tahlequah Cable TV',
    },
    'tct': {
        'name': 'TCT',
    },
    'tel050': {
        'name': 'Tele-Media Company',
    },
    'com050': {
        'name': 'The Community Agency',
    },
    'thr020': {
        'name': 'Three River',
    },
    'cab140': {
        'name': 'Town & Country Technologies',
    },
    'tra010': {
        'name': 'Trans-Video',
    },
    'tre010': {
        'name': 'Trenton TV Cable Company',
    },
    'tcc': {
        'name': 'Tri County Communications Cooperative',
    },
    'tri025': {
        'name': 'TriCounty Telecom',
    },
    'tri110': {
        'name': 'TrioTel Communications, Inc.',
    },
    'tro010': {
        'name': 'Troy Cablevision, Inc.',
    },
    'tsc': {
        'name': 'TSC',
    },
    'cit220': {
        'name': 'Tullahoma Utilities Board',
    },
    'tvc030': {
        'name': 'TV Cable of Rensselaer',
    },
    'tvc015': {
        'name': 'TVC Cable',
    },
    'cab180': {
        'name': 'TVision',
    },
    'twi040': {
        'name': 'Twin Lakes',
    },
    'tvtinc': {
        'name': 'Twin Valley',
    },
    'uis010': {
        'name': 'Union Telephone Company',
    },
    'uni110': {
        'name': 'United Communications - TN',
    },
    'uni120': {
        'name': 'United Services',
    },
    'uss020': {
        'name': 'US Sonet',
    },
    'cab060': {
        'name': 'USA Communications',
    },
    'she005': {
        'name': 'USA Communications/Shellsburg, IA',
    },
    'val040': {
        'name': 'Valley TeleCom Group',
    },
    'val025': {
        'name': 'Valley Telecommunications',
    },
    'val030': {
        'name': 'Valparaiso Broadband',
    },
    'cla050': {
        'name': 'Vast Broadband',
    },
    'sul015': {
        'name': 'Venture Communications Cooperative, Inc.',
    },
    'ver025': {
        'name': 'Vernon Communications Co-op',
    },
    'weh010-vicksburg': {
        'name': 'Vicksburg Video',
    },
    'vis070': {
        'name': 'Vision Communications',
    },
    'volcanotel': {
        'name': 'Volcano Vision, Inc.',
    },
    'vol040-02': {
        'name': 'VolFirst / BLTV',
    },
    'ver070': {
        'name': 'VTel',
    },
    'nttcvtx010': {
        'name': 'VTX1',
    },
    'bci010-02': {
        'name': 'Vyve Broadband',
    },
    'wab020': {
        'name': 'Wabash Mutual Telephone',
    },
    'waitsfield': {
        'name': 'Waitsfield Cable',
    },
    'wal010': {
        'name': 'Walnut Communications',
    },
    'wavebroadband': {
        'name': 'Wave',
    },
    'wav030': {
        'name': 'Waverly Communications Utility',
    },
    'wbi010': {
        'name': 'WBI',
    },
    'web020': {
        'name': 'Webster-Calhoun Cooperative Telephone Association',
    },
    'wes005': {
        'name': 'West Alabama TV Cable',
    },
    'carolinata': {
        'name': 'West Carolina Communications',
    },
    'wct010': {
        'name': 'West Central Telephone Association',
    },
    'wes110': {
        'name': 'West River Cooperative Telephone Company',
    },
    'ani030': {
        'name': 'WesTel Systems',
    },
    'westianet': {
        'name': 'Western Iowa Networks',
    },
    'nttcwhi010': {
        'name': 'Whidbey Telecom',
    },
    'weh010-white': {
        'name': 'White County Cable TV',
    },
    'wes130': {
        'name': 'Wiatel',
    },
    'wik010': {
        'name': 'Wiktel',
    },
    'wil070': {
        'name': 'Wilkes Communications, Inc./RiverStreet Networks',
    },
    'wil015': {
        'name': 'Wilson Communications',
    },
    'win010': {
        'name': 'Windomnet/SMBS',
    },
    'win090': {
        'name': 'Windstream Cable TV',
    },
    'wcta': {
        'name': 'Winnebago Cooperative Telecom Association',
    },
    'wtc010': {
        'name': 'WTC',
    },
    'wil040': {
        'name': 'WTC Communications, Inc.',
    },
    'wya010': {
        'name': 'Wyandotte Cable',
    },
    'hin020-02': {
        'name': 'X-Stream Services',
    },
    'xit010': {
        'name': 'XIT Communications',
    },
    'yel010': {
        'name': 'Yelcot Communications',
    },
    'mid180-01': {
        'name': 'yondoo',
    },
    'cou060': {
        'name': 'Zito Media',
    },
    'slingtv': {
        'name': 'Sling TV',
        'username_field': 'username',
        'password_field': 'password',
    },
    'Suddenlink': {
        'name': 'Suddenlink',
        'username_field': 'username',
        'password_field': 'password',
    },
    'AlticeOne': {
        'name': 'Optimum TV',
        'username_field': 'j_username',
        'password_field': 'j_password',
    },
}


class AdobePassIE(InfoExtractor):  # XXX: Conventionally, base classes should end with BaseIE/InfoExtractor
    _SERVICE_PROVIDER_TEMPLATE = 'https://sp.auth.adobe.com/adobe-services/%s'
    _USER_AGENT = 'Mozilla/5.0 (X11; Linux i686; rv:47.0) Gecko/20100101 Firefox/47.0'
    _MVPD_CACHE = 'ap-mvpd'

    _DOWNLOADING_LOGIN_PAGE = 'Downloading Provider Login Page'

    def _download_webpage_handle(self, *args, **kwargs):
        headers = self.geo_verification_headers()
        headers.update(kwargs.get('headers', {}))
        kwargs['headers'] = headers
        return super()._download_webpage_handle(
            *args, **kwargs)

    @staticmethod
    def _get_mvpd_resource(provider_id, title, guid, rating):
        channel = etree.Element('channel')
        channel_title = etree.SubElement(channel, 'title')
        channel_title.text = provider_id
        item = etree.SubElement(channel, 'item')
        resource_title = etree.SubElement(item, 'title')
        resource_title.text = title
        resource_guid = etree.SubElement(item, 'guid')
        resource_guid.text = guid
        resource_rating = etree.SubElement(item, 'media:rating')
        resource_rating.attrib = {'scheme': 'urn:v-chip'}
        resource_rating.text = rating
        return '<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">' + etree.tostring(channel).decode() + '</rss>'

    def _extract_mvpd_auth(self, url, video_id, requestor_id, resource):
        def xml_text(xml_str, tag):
            return self._search_regex(
                f'<{tag}>(.+?)</{tag}>', xml_str, tag)

        def is_expired(token, date_ele):
            token_expires = unified_timestamp(re.sub(r'[_ ]GMT', '', xml_text(token, date_ele)))
            return token_expires and token_expires <= int(time.time())

        def post_form(form_page_res, note, data={}):
            form_page, urlh = form_page_res
            post_url = self._html_search_regex(r'<form[^>]+action=(["\'])(?P<url>.+?)\1', form_page, 'post url', group='url')
            if not re.match(r'https?://', post_url):
                post_url = urllib.parse.urljoin(urlh.url, post_url)
            form_data = self._hidden_inputs(form_page)
            form_data.update(data)
            return self._download_webpage_handle(
                post_url, video_id, note, data=urlencode_postdata(form_data), headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                })

        def raise_mvpd_required():
            raise ExtractorError(
                'This video is only available for users of participating TV providers. '
                'Use --ap-mso to specify Adobe Pass Multiple-system operator Identifier '
                'and --ap-username and --ap-password or --netrc to provide account credentials.', expected=True)

        def extract_redirect_url(html, url=None, fatal=False):
            # TODO: eliminate code duplication with generic extractor and move
            # redirection code into _download_webpage_handle
            REDIRECT_REGEX = r'[0-9]{,2};\s*(?:URL|url)=\'?([^\'"]+)'
            redirect_url = self._search_regex(
                r'(?i)<meta\s+(?=(?:[a-z-]+="[^"]+"\s+)*http-equiv="refresh")'
                rf'(?:[a-z-]+="[^"]+"\s+)*?content="{REDIRECT_REGEX}',
                html, 'meta refresh redirect',
                default=NO_DEFAULT if fatal else None, fatal=fatal)
            if not redirect_url:
                return None
            if url:
                redirect_url = urllib.parse.urljoin(url, unescapeHTML(redirect_url))
            return redirect_url

        mvpd_headers = {
            'ap_42': 'anonymous',
            'ap_11': 'Linux i686',
            'ap_z': self._USER_AGENT,
            'User-Agent': self._USER_AGENT,
        }

        guid = xml_text(resource, 'guid') if '<' in resource else resource
        count = 0
        while count < 2:
            requestor_info = self.cache.load(self._MVPD_CACHE, requestor_id) or {}
            authn_token = requestor_info.get('authn_token')
            if authn_token and is_expired(authn_token, 'simpleTokenExpires'):
                authn_token = None
            if not authn_token:
                mso_id = self.get_param('ap_mso')
                if mso_id:
                    username, password = self._get_login_info('ap_username', 'ap_password', mso_id)
                    if not username or not password:
                        raise_mvpd_required()
                    mso_info = MSO_INFO[mso_id]

                    provider_redirect_page_res = self._download_webpage_handle(
                        self._SERVICE_PROVIDER_TEMPLATE % 'authenticate/saml', video_id,
                        'Downloading Provider Redirect Page', query={
                            'noflash': 'true',
                            'mso_id': mso_id,
                            'requestor_id': requestor_id,
                            'no_iframe': 'false',
                            'domain_name': 'adobe.com',
                            'redirect_url': url,
                        })
                elif not self._cookies_passed:
                    raise_mvpd_required()

                if not mso_id:
                    pass
                elif mso_id == 'Comcast_SSO':
                    # Comcast page flow varies by video site and whether you
                    # are on Comcast's network.
                    provider_redirect_page, urlh = provider_redirect_page_res
                    if 'automatically signing you in' in provider_redirect_page:
                        oauth_redirect_url = self._html_search_regex(
                            r'window\.location\s*=\s*[\'"]([^\'"]+)',
                            provider_redirect_page, 'oauth redirect')
                        self._download_webpage(
                            oauth_redirect_url, video_id, 'Confirming auto login')
                    elif 'automatically signed in with' in provider_redirect_page:
                        # Seems like comcast is rolling up new way of automatically signing customers
                        oauth_redirect_url = self._html_search_regex(
                            r'continue:\s*"(https://oauth\.xfinity\.com/oauth/authorize\?.+)"', provider_redirect_page,
                            'oauth redirect (signed)')
                        # Just need to process the request. No useful data comes back
                        self._download_webpage(oauth_redirect_url, video_id, 'Confirming auto login')
                    else:
                        if '<form name="signin"' in provider_redirect_page:
                            provider_login_page_res = provider_redirect_page_res
                        elif 'http-equiv="refresh"' in provider_redirect_page:
                            oauth_redirect_url = extract_redirect_url(
                                provider_redirect_page, fatal=True)
                            provider_login_page_res = self._download_webpage_handle(
                                oauth_redirect_url, video_id,
                                self._DOWNLOADING_LOGIN_PAGE)
                        else:
                            provider_login_page_res = post_form(
                                provider_redirect_page_res,
                                self._DOWNLOADING_LOGIN_PAGE)

                        mvpd_confirm_page_res = post_form(
                            provider_login_page_res, 'Logging in', {
                                mso_info['username_field']: username,
                                mso_info['password_field']: password,
                            })
                        mvpd_confirm_page, urlh = mvpd_confirm_page_res
                        if '<button class="submit" value="Resume">Resume</button>' in mvpd_confirm_page:
                            post_form(mvpd_confirm_page_res, 'Confirming Login')
                elif mso_id == 'Philo':
                    # Philo has very unique authentication method
                    self._download_webpage(
                        'https://idp.philo.com/auth/init/login_code', video_id, 'Requesting auth code', data=urlencode_postdata({
                            'ident': username,
                            'device': 'web',
                            'send_confirm_link': False,
                            'send_token': True,
                        }))
                    philo_code = getpass.getpass('Type auth code you have received [Return]: ')
                    self._download_webpage(
                        'https://idp.philo.com/auth/update/login_code', video_id, 'Submitting token', data=urlencode_postdata({
                            'token': philo_code,
                        }))
                    mvpd_confirm_page_res = self._download_webpage_handle('https://idp.philo.com/idp/submit', video_id, 'Confirming Philo Login')
                    post_form(mvpd_confirm_page_res, 'Confirming Login')
                elif mso_id == 'Verizon':
                    # In general, if you're connecting from a Verizon-assigned IP,
                    # you will not actually pass your credentials.
                    provider_redirect_page, urlh = provider_redirect_page_res
                    # From non-Verizon IP, still gave 'Please wait', but noticed N==Y; will need to try on Verizon IP
                    if 'Please wait ...' in provider_redirect_page and '\'N\'== "Y"' not in provider_redirect_page:
                        saml_redirect_url = self._html_search_regex(
                            r'self\.parent\.location=(["\'])(?P<url>.+?)\1',
                            provider_redirect_page,
                            'SAML Redirect URL', group='url')
                        saml_login_page = self._download_webpage(
                            saml_redirect_url, video_id,
                            'Downloading SAML Login Page')
                    elif 'Verizon FiOS - sign in' in provider_redirect_page:
                        # FXNetworks from non-Verizon IP
                        saml_login_page_res = post_form(
                            provider_redirect_page_res, 'Logging in', {
                                mso_info['username_field']: username,
                                mso_info['password_field']: password,
                            })
                        saml_login_page, urlh = saml_login_page_res
                        if 'Please try again.' in saml_login_page:
                            raise ExtractorError(
                                'We\'re sorry, but either the User ID or Password entered is not correct.')
                    else:
                        # ABC from non-Verizon IP
                        saml_redirect_url = self._html_search_regex(
                            r'var\surl\s*=\s*(["\'])(?P<url>.+?)\1',
                            provider_redirect_page,
                            'SAML Redirect URL', group='url')
                        saml_redirect_url = saml_redirect_url.replace(r'\/', '/')
                        saml_redirect_url = saml_redirect_url.replace(r'\-', '-')
                        saml_redirect_url = saml_redirect_url.replace(r'\x26', '&')
                        saml_login_page = self._download_webpage(
                            saml_redirect_url, video_id,
                            'Downloading SAML Login Page')
                        saml_login_page, urlh = post_form(
                            [saml_login_page, saml_redirect_url], 'Logging in', {
                                mso_info['username_field']: username,
                                mso_info['password_field']: password,
                            })
                        if 'Please try again.' in saml_login_page:
                            raise ExtractorError(
                                'Failed to login, incorrect User ID or Password.')
                    saml_login_url = self._search_regex(
                        r'xmlHttp\.open\("POST"\s*,\s*(["\'])(?P<url>.+?)\1',
                        saml_login_page, 'SAML Login URL', group='url')
                    saml_response_json = self._download_json(
                        saml_login_url, video_id, 'Downloading SAML Response',
                        headers={'Content-Type': 'text/xml'})
                    self._download_webpage(
                        saml_response_json['targetValue'], video_id,
                        'Confirming Login', data=urlencode_postdata({
                            'SAMLResponse': saml_response_json['SAMLResponse'],
                            'RelayState': saml_response_json['RelayState'],
                        }), headers={
                            'Content-Type': 'application/x-www-form-urlencoded',
                        })
                elif mso_id in ('Spectrum', 'Charter_Direct'):
                    # Spectrum's login for is dynamically loaded via JS so we need to hardcode the flow
                    # as a one-off implementation.
                    provider_redirect_page, urlh = provider_redirect_page_res
                    provider_login_page_res = post_form(
                        provider_redirect_page_res, self._DOWNLOADING_LOGIN_PAGE)
                    saml_login_page, urlh = provider_login_page_res
                    relay_state = self._search_regex(
                        r'RelayState\s*=\s*"(?P<relay>.+?)";',
                        saml_login_page, 'RelayState', group='relay')
                    saml_request = self._search_regex(
                        r'SAMLRequest\s*=\s*"(?P<saml_request>.+?)";',
                        saml_login_page, 'SAMLRequest', group='saml_request')
                    login_json = {
                        mso_info['username_field']: username,
                        mso_info['password_field']: password,
                        'RelayState': relay_state,
                        'SAMLRequest': saml_request,
                    }
                    saml_response_json = self._download_json(
                        'https://tveauthn.spectrum.net/tveauthentication/api/v1/manualAuth', video_id,
                        'Downloading SAML Response',
                        data=json.dumps(login_json).encode(),
                        headers={
                            'Content-Type': 'application/json',
                            'Accept': 'application/json',
                        })
                    self._download_webpage(
                        saml_response_json['SAMLRedirectUri'], video_id,
                        'Confirming Login', data=urlencode_postdata({
                            'SAMLResponse': saml_response_json['SAMLResponse'],
                            'RelayState': relay_state,
                        }), headers={
                            'Content-Type': 'application/x-www-form-urlencoded',
                        })
                elif mso_id == 'slingtv':
                    # SlingTV has a meta-refresh based authentication, but also
                    # looks at the tab history to count the number of times the
                    # browser has been on a page

                    first_bookend_page, urlh = provider_redirect_page_res

                    hidden_data = self._hidden_inputs(first_bookend_page)
                    hidden_data['history'] = 1

                    provider_login_page_res = self._download_webpage_handle(
                        urlh.url, video_id, 'Sending first bookend',
                        query=hidden_data)

                    provider_association_redirect, urlh = post_form(
                        provider_login_page_res, 'Logging in', {
                            mso_info['username_field']: username,
                            mso_info['password_field']: password,
                        })

                    provider_refresh_redirect_url = extract_redirect_url(
                        provider_association_redirect, url=urlh.url)

                    last_bookend_page, urlh = self._download_webpage_handle(
                        provider_refresh_redirect_url, video_id,
                        'Downloading Auth Association Redirect Page')
                    hidden_data = self._hidden_inputs(last_bookend_page)
                    hidden_data['history'] = 3

                    mvpd_confirm_page_res = self._download_webpage_handle(
                        urlh.url, video_id, 'Sending final bookend',
                        query=hidden_data)

                    post_form(mvpd_confirm_page_res, 'Confirming Login')
                elif mso_id == 'Suddenlink':
                    # Suddenlink is similar to SlingTV in using a tab history count and a meta refresh,
                    # but they also do a dynmaic redirect using javascript that has to be followed as well
                    first_bookend_page, urlh = post_form(
                        provider_redirect_page_res, 'Pressing Continue...')

                    hidden_data = self._hidden_inputs(first_bookend_page)
                    hidden_data['history_val'] = 1

                    provider_login_redirect_page_res = self._download_webpage_handle(
                        urlh.url, video_id, 'Sending First Bookend',
                        query=hidden_data)

                    provider_login_redirect_page, urlh = provider_login_redirect_page_res

                    # Some website partners seem to not have the extra ajaxurl redirect step, so we check if we already
                    # have the login prompt or not
                    if 'id="password" type="password" name="password"' in provider_login_redirect_page:
                        provider_login_page_res = provider_login_redirect_page_res
                    else:
                        provider_tryauth_url = self._html_search_regex(
                            r'url:\s*[\'"]([^\'"]+)', provider_login_redirect_page, 'ajaxurl')
                        provider_tryauth_page = self._download_webpage(
                            provider_tryauth_url, video_id, 'Submitting TryAuth',
                            query=hidden_data)

                        provider_login_page_res = self._download_webpage_handle(
                            f'https://authorize.suddenlink.net/saml/module.php/authSynacor/login.php?AuthState={provider_tryauth_page}',
                            video_id, 'Getting Login Page',
                            query=hidden_data)

                    provider_association_redirect, urlh = post_form(
                        provider_login_page_res, 'Logging in', {
                            mso_info['username_field']: username,
                            mso_info['password_field']: password,
                        })

                    provider_refresh_redirect_url = extract_redirect_url(
                        provider_association_redirect, url=urlh.url)

                    last_bookend_page, urlh = self._download_webpage_handle(
                        provider_refresh_redirect_url, video_id,
                        'Downloading Auth Association Redirect Page')

                    hidden_data = self._hidden_inputs(last_bookend_page)
                    hidden_data['history_val'] = 3

                    mvpd_confirm_page_res = self._download_webpage_handle(
                        urlh.url, video_id, 'Sending Final Bookend',
                        query=hidden_data)

                    post_form(mvpd_confirm_page_res, 'Confirming Login')
                else:
                    # Some providers (e.g. DIRECTV NOW) have another meta refresh
                    # based redirect that should be followed.
                    provider_redirect_page, urlh = provider_redirect_page_res
                    provider_refresh_redirect_url = extract_redirect_url(
                        provider_redirect_page, url=urlh.url)
                    if provider_refresh_redirect_url:
                        provider_redirect_page_res = self._download_webpage_handle(
                            provider_refresh_redirect_url, video_id,
                            'Downloading Provider Redirect Page (meta refresh)')
                    provider_login_page_res = post_form(
                        provider_redirect_page_res, self._DOWNLOADING_LOGIN_PAGE)
                    form_data = {
                        mso_info.get('username_field', 'username'): username,
                        mso_info.get('password_field', 'password'): password,
                    }
                    if mso_id in ('Cablevision', 'AlticeOne'):
                        form_data['_eventId_proceed'] = ''
                    mvpd_confirm_page_res = post_form(provider_login_page_res, 'Logging in', form_data)
                    if mso_id != 'Rogers':
                        post_form(mvpd_confirm_page_res, 'Confirming Login')

                try:
                    session = self._download_webpage(
                        self._SERVICE_PROVIDER_TEMPLATE % 'session', video_id,
                        'Retrieving Session', data=urlencode_postdata({
                            '_method': 'GET',
                            'requestor_id': requestor_id,
                        }), headers=mvpd_headers)
                except ExtractorError as e:
                    if not mso_id and isinstance(e.cause, HTTPError) and e.cause.status == 401:
                        raise_mvpd_required()
                    raise
                if '<pendingLogout' in session:
                    self.cache.store(self._MVPD_CACHE, requestor_id, {})
                    count += 1
                    continue
                authn_token = unescapeHTML(xml_text(session, 'authnToken'))
                requestor_info['authn_token'] = authn_token
                self.cache.store(self._MVPD_CACHE, requestor_id, requestor_info)

            authz_token = requestor_info.get(guid)
            if authz_token and is_expired(authz_token, 'simpleTokenTTL'):
                authz_token = None
            if not authz_token:
                authorize = self._download_webpage(
                    self._SERVICE_PROVIDER_TEMPLATE % 'authorize', video_id,
                    'Retrieving Authorization Token', data=urlencode_postdata({
                        'resource_id': resource,
                        'requestor_id': requestor_id,
                        'authentication_token': authn_token,
                        'mso_id': xml_text(authn_token, 'simpleTokenMsoID'),
                        'userMeta': '1',
                    }), headers=mvpd_headers)
                if '<pendingLogout' in authorize:
                    self.cache.store(self._MVPD_CACHE, requestor_id, {})
                    count += 1
                    continue
                if '<error' in authorize:
                    raise ExtractorError(xml_text(authorize, 'details'), expected=True)
                authz_token = unescapeHTML(xml_text(authorize, 'authzToken'))
                requestor_info[guid] = authz_token
                self.cache.store(self._MVPD_CACHE, requestor_id, requestor_info)

            mvpd_headers.update({
                'ap_19': xml_text(authn_token, 'simpleSamlNameID'),
                'ap_23': xml_text(authn_token, 'simpleSamlSessionIndex'),
            })

            short_authorize = self._download_webpage(
                self._SERVICE_PROVIDER_TEMPLATE % 'shortAuthorize',
                video_id, 'Retrieving Media Token', data=urlencode_postdata({
                    'authz_token': authz_token,
                    'requestor_id': requestor_id,
                    'session_guid': xml_text(authn_token, 'simpleTokenAuthenticationGuid'),
                    'hashed_guid': 'false',
                }), headers=mvpd_headers)
            if '<pendingLogout' in short_authorize:
                self.cache.store(self._MVPD_CACHE, requestor_id, {})
                count += 1
                continue
            return short_authorize
