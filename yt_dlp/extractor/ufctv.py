from .imggaming import ImgGamingBaseIE


class UFCTVIE(ImgGamingBaseIE):
    _VALID_URL = ImgGamingBaseIE._VALID_URL_TEMPL % r'(?:(?:app|www)\.)?(?:ufc\.tv|(?:ufc)?fightpass\.com)|ufcfightpass\.img(?:dge|gaming)\.com'
    _NETRC_MACHINE = 'ufctv'
    _REALM = 'ufc'


class UFCArabiaIE(ImgGamingBaseIE):
    _VALID_URL = ImgGamingBaseIE._VALID_URL_TEMPL % r'(?:(?:app|www)\.)?ufcarabia\.(?:ae|com)'
    _NETRC_MACHINE = 'ufcarabia'
    _REALM = 'admufc'
