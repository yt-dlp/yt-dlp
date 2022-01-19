# coding: utf-8
from __future__ import unicode_literals

import base64
import hashlib
import json
import random
import re
import time

from .common import InfoExtractor
from ..aes import aes_encrypt
from ..compat import compat_str
from ..utils import (
    bytes_to_intlist,
    determine_ext,
    intlist_to_bytes,
    int_or_none,
    join_nonempty,
    strip_jsonp,
    unescapeHTML,
    unsmuggle_url,
)

# This import causes a ModuleNotFoundError on some systems for unknown reason.
# See issues:
# https://github.com/yt-dlp/yt-dlp/issues/35
# https://github.com/ytdl-org/youtube-dl/issues/27449
# https://github.com/animelover1984/youtube-dl/issues/17
try:
    from .anvato_token_generator import NFLTokenGenerator
except ImportError:
    NFLTokenGenerator = None


def md5_text(s):
    if not isinstance(s, compat_str):
        s = compat_str(s)
    return hashlib.md5(s.encode('utf-8')).hexdigest()


class AnvatoIE(InfoExtractor):
    _VALID_URL = r'anvato:(?P<access_key_or_mcp>[^:]+):(?P<id>\d+)'

    # Copied from anvplayer.min.js
    _ANVACK_TABLE = {
        'nbcu_nbcd_desktop_web_prod_93d8ead38ce2024f8f544b78306fbd15895ae5e6': 'NNemUkySjxLyPTKvZRiGntBIjEyK8uqicjMakIaQ',
        'nbcu_nbcd_desktop_web_qa_1a6f01bdd0dc45a439043b694c8a031d': 'eSxJUbA2UUKBTXryyQ2d6NuM8oEqaPySvaPzfKNA',
        'nbcu_nbcd_desktop_web_acc_eb2ff240a5d4ae9a63d4c297c32716b6c523a129': '89JR3RtUGbvKuuJIiKOMK0SoarLb5MUx8v89RcbP',
        'nbcu_nbcd_watchvod_web_prod_e61107507180976724ec8e8319fe24ba5b4b60e1': 'Uc7dFt7MJ9GsBWB5T7iPvLaMSOt8BBxv4hAXk5vv',
        'nbcu_nbcd_watchvod_web_qa_42afedba88a36203db5a4c09a5ba29d045302232': 'T12oDYVFP2IaFvxkmYMy5dKxswpLHtGZa4ZAXEi7',
        'nbcu_nbcd_watchvod_web_acc_9193214448e2e636b0ffb78abacfd9c4f937c6ca': 'MmobcxUxMedUpohNWwXaOnMjlbiyTOBLL6d46ZpR',
        'nbcu_local_monitor_web_acc_f998ad54eaf26acd8ee033eb36f39a7b791c6335': 'QvfIoPYrwsjUCcASiw3AIkVtQob2LtJHfidp9iWg',
        'nbcu_cable_monitor_web_acc_a413759603e8bedfcd3c61b14767796e17834077': 'uwVPJLShvJWSs6sWEIuVem7MTF8A4IknMMzIlFto',
        'nbcu_nbcd_mcpstage_web_qa_4c43a8f6e95a88dbb40276c0630ba9f693a63a4e': 'PxVYZVwjhgd5TeoPRxL3whssb5OUPnM3zyAzq8GY',
        'nbcu_comcast_comcast_web_prod_074080762ad4ce956b26b43fb22abf153443a8c4': 'afnaRZfDyg1Z3WZHdupKfy6xrbAG2MHqe3VfuSwh',
        'nbcu_comcast_comcast_web_qa_706103bb93ead3ef70b1de12a0e95e3c4481ade0': 'DcjsVbX9b3uoPlhdriIiovgFQZVxpISZwz0cx1ZK',
        'nbcu_comcast_comcastcable_web_prod_669f04817536743563d7331c9293e59fbdbe3d07': '0RwMN2cWy10qhAhOscq3eK7aEe0wqnKt3vJ0WS4D',
        'nbcu_comcast_comcastcable_web_qa_3d9d2d66219094127f0f6b09cc3c7bb076e3e1ca': '2r8G9DEya7PCqBceKZgrn2XkXgASjwLMuaFE1Aad',
        'hearst_hearst_demo_web_stage_960726dfef3337059a01a78816e43b29ec04dfc7': 'cuZBPXTR6kSdoTCVXwk5KGA8rk3NrgGn4H6e9Dsp',
        'anvato_mcpqa_demo_web_stage_18b55e00db5a13faa8d03ae6e41f6f5bcb15b922': 'IOaaLQ8ymqVyem14QuAvE5SndQynTcH5CrLkU2Ih',
        'anvato_nextmedia_demo_web_stage_9787d56a02ff6b9f43e9a2b0920d8ca88beb5818': 'Pqu9zVzI1ApiIzbVA3VkGBEQHvdKSUuKpD6s2uaR',
        'anvato_scripps_app_web_prod_0837996dbe373629133857ae9eb72e740424d80a': 'du1ccmn7RxzgizwbWU7hyUaGodNlJn7HtXI0WgXW',
        'anvato_scripps_app_web_stage_360797e00fe2826be142155c4618cc52fce6c26c': '2PMrQ0BRoqCWl7nzphj0GouIMEh2mZYivAT0S1Su',
        'fs2go_fs2go_go_all_prod_21934911ccfafc03a075894ead2260d11e2ddd24': 'RcuHlKikW2IJw6HvVoEkqq2UsuEJlbEl11pWXs4Q',
        'fs2go_fs2go_go_web_prod_ead4b0eec7460c1a07783808db21b49cf1f2f9a7': '4K0HTT2u1zkQA2MaGaZmkLa1BthGSBdr7jllrhk5',
        'fs2go_fs2go_go_web_stage_407585454a4400355d4391691c67f361': 'ftnc37VKRJBmHfoGGi3kT05bHyeJzilEzhKJCyl3',
        'fs2go_fs2go_go_android_stage_44b714db6f8477f29afcba15a41e1d30': 'CtxpPvVpo6AbZGomYUhkKs7juHZwNml9b9J0J2gI',
        'anvato_cbslocal_app_web_prod_547f3e49241ef0e5d30c79b2efbca5d92c698f67': 'Pw0XX5KBDsyRnPS0R2JrSrXftsy8Jnz5pAjaYC8s',
        'anvato_cbslocal_app_web_stage_547a5f096594cd3e00620c6f825cad1096d28c80': '37OBUhX2uwNyKhhrNzSSNHSRPZpApC3trdqDBpuz',
        'fs2go_att_att_web_prod_1042dddd089a05438b6a08f972941176f699ffd8': 'JLcF20JwYvpv6uAGcLWIaV12jKwaL1R8us4b6Zkg',
        'fs2go_att_att_web_stage_807c5001955fc114a3331fe027ddc76e': 'gbu1oO1y0JiOFh4SUipt86P288JHpyjSqolrrT1x',
        'fs2go_fs2go_tudor_web_prod_a7dd8e5a7cdc830cae55eae6f3e9fee5ee49eb9b': 'ipcp87VCEZXPPe868j3orLqzc03oTy7DXsGkAXXH',
        'anvato_mhz_app_web_prod_b808218b30de7fdf60340cbd9831512bc1bf6d37': 'Stlm5Gs6BEhJLRTZHcNquyzxGqr23EuFmE5DCgjX',
        'fs2go_charter_charter_web_stage_c2c6e5a68375a1bf00fff213d3ff8f61a835a54c': 'Lz4hbJp1fwL6jlcz4M2PMzghM4jp4aAmybtT5dPc',
        'fs2go_charter_charter_web_prod_ebfe3b10f1af215a7321cd3d629e0b81dfa6fa8c': 'vUJsK345A1bVmyYDRhZX0lqFIgVXuqhmuyp1EtPK',
        'anvato_epfox_app_web_prod_b3373168e12f423f41504f207000188daf88251b': 'GDKq1ixvX3MoBNdU5IOYmYa2DTUXYOozPjrCJnW7',
        'anvato_epfox_app_web_stage_a3c2ce60f8f83ef374a88b68ee73a950f8ab87ce': '2jz2NH4BsXMaDsoJ5qkHMbcczAfIReo2eFYuVC1C',
        'fs2go_verizon_verizon_web_stage_08e6df0354a4803f1b1f2428b5a9a382e8dbcd62': 'rKTVapNaAcmnUbGL4ZcuOoY4SE7VmZSQsblPFr7e',
        'fs2go_verizon_verizon_web_prod_f909564cb606eff1f731b5e22e0928676732c445': 'qLSUuHerM3u9eNPzaHyUK52obai5MvE4XDJfqYe1',
        'fs2go_foxcom_synd_web_stage_f7b9091f00ea25a4fdaaae77fca5b54cdc7e7043': '96VKF2vLd24fFiDfwPFpzM5llFN4TiIGAlodE0Re',
        'fs2go_foxcom_synd_web_prod_0f2cdd64d87e4ab6a1d54aada0ff7a7c8387a064': 'agiPjbXEyEZUkbuhcnmVPhe9NNVbDjCFq2xkcx51',
        'anvato_own_app_web_stage_1214ade5d28422c4dae9d03c1243aba0563c4dba': 'mzhamNac3swG4WsJAiUTacnGIODi6SWeVWk5D7ho',
        'anvato_own_app_web_prod_944e162ed927ec3e9ed13eb68ed2f1008ee7565e': '9TSxh6G2TXOLBoYm9ro3LdNjjvnXpKb8UR8KoIP9',
        'anvato_scripps_app_ftv_prod_a10a10468edd5afb16fb48171c03b956176afad1': 'COJ2i2UIPK7xZqIWswxe7FaVBOVgRkP1F6O6qGoH',
        'anvato_scripps_app_ftv_stage_77d3ad2bdb021ec37ca2e35eb09acd396a974c9a': 'Q7nnopNLe2PPfGLOTYBqxSaRpl209IhqaEuDZi1F',
        'anvato_univision_app_web_stage_551236ef07a0e17718c3995c35586b5ed8cb5031': 'D92PoLS6UitwxDRA191HUGT9OYcOjV6mPMa5wNyo',
        'anvato_univision_app_web_prod_039a5c0a6009e637ae8ac906718a79911e0e65e1': '5mVS5u4SQjtw6NGw2uhMbKEIONIiLqRKck5RwQLR',
        'nbcu_cnbc_springfield_ios_prod_670207fae43d6e9a94c351688851a2ce': 'M7fqCCIP9lW53oJbHs19OlJlpDrVyc2OL8gNeuTa',
        'nbcu_cnbc_springfieldvod_ios_prod_7a5f04b1ceceb0e9c9e2264a44aa236e08e034c2': 'Yia6QbJahW0S7K1I0drksimhZb4UFq92xLBmmMvk',
        'anvato_cox_app_web_prod_ce45cda237969f93e7130f50ee8bb6280c1484ab': 'cc0miZexpFtdoqZGvdhfXsLy7FXjRAOgb9V0f5fZ',
        'anvato_cox_app_web_stage_c23dbe016a8e9d8c7101d10172b92434f6088bf9': 'yivU3MYHd2eDZcOfmLbINVtqxyecKTOp8OjOuoGJ',
        'anvato_chnzero_app_web_stage_b1164d1352b579e792e542fddf13ee34c0eeb46b': 'A76QkXMmVH8lTCfU15xva1mZnSVcqeY4Xb22Kp7m',
        'anvato_chnzero_app_web_prod_253d358928dc08ec161eda2389d53707288a730c': 'OA5QI3ZWZZkdtUEDqh28AH8GedsF6FqzJI32596b',
        'anvato_discovery_vodpoc_web_stage_9fa7077b5e8af1f8355f65d4fb8d2e0e9d54e2b7': 'q3oT191tTQ5g3JCP67PkjLASI9s16DuWZ6fYmry3',
        'anvato_discovery_vodpoc_web_prod_688614983167a1af6cdf6d76343fda10a65223c1': 'qRvRQCTVHd0VVOHsMvvfidyWmlYVrTbjby7WqIuK',
        'nbcu_cnbc_springfieldvod_ftv_stage_826040aad1925a46ac5dfb4b3c5143e648c6a30d': 'JQaSb5a8Tz0PT4ti329DNmzDO30TnngTHmvX8Vua',
        'nbcu_cnbc_springfield_ftv_stage_826040aad1925a46ac5dfb4b3c5143e648c6a30d': 'JQaSb5a8Tz0PT4ti329DNmzDO30TnngTHmvX8Vua',
        'nbcu_nbcd_capture_web_stage_4dd9d585bfb984ebf856dee35db027b2465cc4ae': '0j1Ov4Vopyi2HpBZJYdL2m8ERJVGYh3nNpzPiO8F',
        'nbcu_nbcd_watch3_android_prod_7712ca5fcf1c22f19ec1870a9650f9c37db22dcf': '3LN2UB3rPUAMu7ZriWkHky9vpLMXYha8JbSnxBlx',
        'nbcu_nbcd_watchvod3_android_prod_0910a3a4692d57c0b5ff4316075bc5d096be45b9': 'mJagcQ2II30vUOAauOXne7ERwbf5S9nlB3IP17lQ',
        'anvato_scripps_app_atv_prod_790deda22e16e71e83df58f880cd389908a45d52': 'CB6trI1mpoDIM5o54DNTsji90NDBQPZ4z4RqBNSH',
        'nbcu_nbcd_watchv4_android_prod_ff67cef9cb409158c6f8c3533edddadd0b750507': 'j8CHQCUWjlYERj4NFRmUYOND85QNbHViH09UwuKm',
        'nbcu_nbcd_watchvodv4_android_prod_a814d781609989dea6a629d50ae4c7ad8cc8e907': 'rkVnUXxdA9rawVLUlDQtMue9Y4Q7lFEaIotcUhjt',
        'rvVKpA50qlOPLFxMjrCGf5pdkdQDm7qn': '1J7ZkY5Qz5lMLi93QOH9IveE7EYB3rLl',
        'nbcu_dtv_local_web_prod_b266cf49defe255fd4426a97e27c09e513e9f82f': 'HuLnJDqzLa4saCzYMJ79zDRSQpEduw1TzjMNQu2b',
        'nbcu_att_local_web_prod_4cef038b2d969a6b7d700a56a599040b6a619f67': 'Q0Em5VDc2KpydUrVwzWRXAwoNBulWUxCq2faK0AV',
        'nbcu_dish_local_web_prod_c56dcaf2da2e9157a4266c82a78195f1dd570f6b': 'bC1LWmRz9ayj2AlzizeJ1HuhTfIaJGsDBnZNgoRg',
        'nbcu_verizon_local_web_prod_88bebd2ce006d4ed980de8133496f9a74cb9b3e1': 'wzhDKJZpgvUSS1EQvpCQP8Q59qVzcPixqDGJefSk',
        'nbcu_charter_local_web_prod_9ad90f7fc4023643bb718f0fe0fd5beea2382a50': 'PyNbxNhEWLzy1ZvWEQelRuIQY88Eub7xbSVRMdfT',
        'nbcu_suddenlink_local_web_prod_20fb711725cac224baa1c1cb0b1c324d25e97178': '0Rph41lPXZbb3fqeXtHjjbxfSrNbtZp1Ygq7Jypa',
        'nbcu_wow_local_web_prod_652d9ce4f552d9c2e7b5b1ed37b8cb48155174ad': 'qayIBZ70w1dItm2zS42AptXnxW15mkjRrwnBjMPv',
        'nbcu_centurylink_local_web_prod_2034402b029bf3e837ad46814d9e4b1d1345ccd5': 'StePcPMkjsX51PcizLdLRMzxMEl5k2FlsMLUNV4k',
        'nbcu_atlanticbrd_local_web_prod_8d5f5ecbf7f7b2f5e6d908dd75d90ae3565f682e': 'NtYLb4TFUS0pRs3XTkyO5sbVGYjVf17bVbjaGscI',
        'nbcu_nbcd_watchvod_web_dev_08bc05699be47c4f31d5080263a8cfadc16d0f7c': 'hwxi2dgDoSWgfmVVXOYZm14uuvku4QfopstXckhr',
        'anvato_nextmedia_app_web_prod_a4fa8c7204aa65e71044b57aaf63711980cfe5a0': 'tQN1oGPYY1nM85rJYePWGcIb92TG0gSqoVpQTWOw',
        'anvato_mcp_lin_web_prod_4c36fbfd4d8d8ecae6488656e21ac6d1ac972749': 'GUXNf5ZDX2jFUpu4WT2Go4DJ5nhUCzpnwDRRUx1K',
        'anvato_mcp_univision_web_prod_37fe34850c99a3b5cdb71dab10a417dd5cdecafa': 'bLDYF8JqfG42b7bwKEgQiU9E2LTIAtnKzSgYpFUH',
        'anvato_mcp_fs2go_web_prod_c7b90a93e171469cdca00a931211a2f556370d0a': 'icgGoYGipQMMSEvhplZX1pwbN69srwKYWksz3xWK',
        'anvato_mcp_sps_web_prod_54bdc90dd6ba21710e9f7074338365bba28da336': 'fA2iQdI7RDpynqzQYIpXALVS83NTPr8LLFK4LFsu',
        'anvato_mcp_anv_web_prod_791407490f4c1ef2a4bcb21103e0cb1bcb3352b3': 'rMOUZqe9lwcGq2mNgG3EDusm6lKgsUnczoOX3mbg',
        'anvato_mcp_gray_web_prod_4c10f067c393ed8fc453d3930f8ab2b159973900': 'rMOUZqe9lwcGq2mNgG3EDusm6lKgsUnczoOX3mbg',
        'anvato_mcp_hearst_web_prod_5356c3de0fc7c90a3727b4863ca7fec3a4524a99': 'P3uXJ0fXXditBPCGkfvlnVScpPEfKmc64Zv7ZgbK',
        'anvato_mcp_cbs_web_prod_02f26581ff80e5bda7aad28226a8d369037f2cbe': 'mGPvo5ZA5SgjOFAPEPXv7AnOpFUICX8hvFQVz69n',
        'anvato_mcp_telemundo_web_prod_c5278d51ad46fda4b6ca3d0ea44a7846a054f582': 'qyT6PXXLjVNCrHaRVj0ugAhalNRS7Ee9BP7LUokD',
        'nbcu_nbcd_watchvodv4_web_stage_4108362fba2d4ede21f262fea3c4162cbafd66c7': 'DhaU5lj0W2gEdcSSsnxURq8t7KIWtJfD966crVDk',
        'anvato_scripps_app_ios_prod_409c41960c60b308db43c3cc1da79cab9f1c3d93': 'WPxj5GraLTkYCyj3M7RozLqIycjrXOEcDGFMIJPn',
        'EZqvRyKBJLrgpClDPDF8I7Xpdp40Vx73': '4OxGd2dEakylntVKjKF0UK9PDPYB6A9W',
        'M2v78QkpleXm9hPp9jUXI63x5vA6BogR': 'ka6K32k7ZALmpINkjJUGUo0OE42Md1BQ',
        'nbcu_nbcd_desktop_web_prod_93d8ead38ce2024f8f544b78306fbd15895ae5e6_secure': 'NNemUkySjxLyPTKvZRiGntBIjEyK8uqicjMakIaQ',
        'X8POa4zPPaKVZHqmWjuEzfP31b1QM9VN': 'Dn5vOY9ooDw7VSl9qztjZI5o0g08mA0z',
        'M2v78QkBMpNJlSPp9diX5F2PBmBy6Bog': 'ka6K32kyo7nDZfNkjQCGWf1lpApXMd1B',
        'bvJ0dQpav07l0hG5JgfVLF2dv1vARwpP': 'BzoQW24GrJZoJfmNodiJKSPeB9B8NOxj',
        'lxQMLg2XZKuEZaWgsqubBxV9INZ6bryY': 'Vm2Mx6noKds9jB71h6urazwlTG3m9x8l',
        '04EnjvXeoSmkbJ9ckPs7oY0mcxv7PlyN': 'aXERQP9LMfQVlEDsgGs6eEA1SWznAQ8P',
        'mQbO2ge6BFRWVPYCYpU06YvNt80XLvAX': 'E2BV1NGmasN5v7eujECVPJgwflnLPm2A',
        'g43oeBzJrCml7o6fa5fRL1ErCdeD8z4K': 'RX34mZ6zVH4Nr6whbxIGLv9WSbxEKo8V',
        'VQrDJoP7mtdBzkxhXbSPwGB1coeElk4x': 'j2VejQx0VFKQepAF7dI0mJLKtOVJE18z',
        'WxA5NzLRjCrmq0NUgaU5pdMDuZO7RJ4w': 'lyY5ADLKaIOLEgAsGQCveEMAcqnx3rY9',
        'M4lpMXB71ie0PjMCjdFzVXq0SeRVqz49': 'n2zVkOqaLIv3GbLfBjcwW51LcveWOZ2e',
        'dyDZGEqN8u8nkJZcJns0oxYmtP7KbGAn': 'VXOEqQW9BtEVLajfZQSLEqxgS5B7qn2D',
        'E7QNjrVY5u5mGvgu67IoDgV1CjEND8QR': 'rz8AaDmdKIkLmPNhB5ILPJnjS5PnlL8d',
        'a4zrqjoKlfzg0dwHEWtP31VqcLBpjm4g': 'LY9J16gwETdGWa3hjBu5o0RzuoQDjqXQ',
        'dQP5BZroMsMVLO1hbmT5r2Enu86GjxA6': '7XR3oOdbPF6x3PRFLDCq9RkgsRjAo48V',
        'M4lKNBO1NFe0PjMCj1tzVXq0SeRVqzA9': 'n2zoRqGLRUv3GbLfBmTwW51LcveWOZYe',
        'nAZ7MZdpGCGg1pqFEbsoJOz2C60mv143': 'dYJgdqA9aT4yojETqGi7yNgoFADxqmXP',
        '3y1MERYgOuE9NzbFgwhV6Wv2F0YKvbyz': '081xpZDQgC4VadLTavhWQxrku56DAgXV',
        'bmQvmEXr5HWklBMCZOcpE2Z3HBYwqGyl': 'zxXPbVNyMiMAZldhr9FkOmA0fl4aKr2v',
        'wA7oDNYldfr6050Hwxi52lPZiVlB86Ap': 'ZYK16aA7ni0d3l3c34uwpxD7CbReMm8Q',
        'g43MbKMWmFml7o7sJoSRkXxZiXRvJ3QK': 'RX3oBJonvs4Nr6rUWBCGn3matRGqJPXV',
        'mA9VdlqpLS0raGaSDvtoqNrBTzb8XY4q': '0XN4OjBD3fnW7r7IbmtJB4AyfOmlrE2r',
        'mAajOwgkGt17oGoFmEuklMP9H0GnW54d': 'lXbBLPGyzikNGeGujAuAJGjZiwLRxyXR',
        'vy8vjJ9kbUwrRqRu59Cj5dWZfzYErlAb': 'K8l7gpwaGcBpnAnCLNCmPZRdin3eaQX0',
        'xQMWBpR8oHEZaWaSMGUb0avOHjLVYn4Y': 'm2MrN4vEaf9jB7BFy5Srb40jTrN67AYl',
        'xyKEmVO3miRr6D6UVkt7oB8jtD6aJEAv': 'g2ddDebqDfqdgKgswyUKwGjbTWwzq923',
        '7Qk0wa2D9FjKapacoJF27aLvUDKkLGA0': 'b2kgBEkephJaMkMTL7s1PLe4Ua6WyP2P',
        '3QLg6nqmNTJ5VvVTo7f508LPidz1xwyY': 'g2L1GgpraipmAOAUqmIbBnPxHOmw4MYa',
        '3y1B7zZjXTE9NZNSzZSVNPZaTNLjo6Qz': '081b5G6wzH4VagaURmcWbN5mT4JGEe2V',
        'lAqnwvkw6SG6D8DSqmUg6DRLUp0w3G4x': 'O2pbP0xPDFNJjpjIEvcdryOJtpkVM4X5',
        'awA7xd1N0Hr6050Hw2c52lPZiVlB864p': 'GZYKpn4aoT0d3l3c3PiwpxD7CbReMmXQ',
        'jQVqPLl9YHL1WGWtR1HDgWBGT63qRNyV': '6X03ne6vrU4oWyWUN7tQVoajikxJR3Ye',
        'GQRMR8mL7uZK797t7xH3eNzPIP5dOny1': 'm2vqPWGd4U31zWzSyasDRAoMT1PKRp8o',
        'zydq9RdmRhXLkNkfNoTJlMzaF0lWekQB': '3X7LnvE7vH5nkEkSqLiey793Un7dLB8e',
        'VQrDzwkB2IdBzjzu9MHPbEYkSB50gR4x': 'j2VebLzoKUKQeEesmVh0gM1eIp9jKz8z',
        'mAa2wMamBs17oGoFmktklMP9H0GnW54d': 'lXbgP74xZTkNGeGujVUAJGjZiwLRxy8R',
        '7yjB6ZLG6sW8R6RF2xcan1KGfJ5dNoyd': 'wXQkPorvPHZ45N5t4Jf6qwg5Tp4xvw29',
        'a4zPpNeWGuzg0m0iX3tPeanGSkRKWXQg': 'LY9oa3QAyHdGW9Wu3Ri5JGeEik7l1N8Q',
        'k2rneA2M38k25cXDwwSknTJlxPxQLZ6M': '61lyA2aEVDzklfdwmmh31saPxQx2VRjp',
        'bK9Zk4OvPnvxduLgxvi8VUeojnjA02eV': 'o5jANYjbeMb4nfBaQvcLAt1jzLzYx6ze',
        '5VD6EydM3R9orHmNMGInGCJwbxbQvGRw': 'w3zjmX7g4vnxzCxElvUEOiewkokXprkZ',
        '70X35QbVYVYNPUmP9YfbzI06YqYQk2R1': 'vG4Aj2BMjMjoztB7zeFOnCVPJpJ8lMOa',
        '26qYwQVG9p1Bks2GgBckjfDJOXOAMgG1': 'r4ev9X0mv5zqJc0yk5IBDcQOwZw8mnwQ',
        'rvVKpA56MBXWlSxMw3cobT5pdkd4Dm7q': '1J7ZkY53pZ645c93owcLZuveE7E8B3rL',
        'qN1zdy1zlYL23IWZGWtDvfV6WeWQWkJo': 'qN1zdy1zlYL23IWZGWtDvfV6WeWQWkJo',
        'jdKqRGF16dKsBviMDae7IGDl7oTjEbVV': 'Q09l7vhlNxPFErIOK6BVCe7KnwUW5DVV',
        '3QLkogW1OUJ5VvPsrDH56DY2u7lgZWyY': 'g2LRE1V9espmAOPhE4ubj4ZdUA57yDXa',
        'wyJvWbXGBSdbkEzhv0CW8meou82aqRy8': 'M2wolPvyBIpQGkbT4juedD4ruzQGdK2y',
        '7QkdZrzEkFjKap6IYDU2PB0oCNZORmA0': 'b2kN1l96qhJaMkPs9dt1lpjBfwqZoA8P',
        'pvA05113MHG1w3JTYxc6DVlRCjErVz4O': 'gQXeAbblBUnDJ7vujbHvbRd1cxlz3AXO',
        'mA9blJDZwT0raG1cvkuoeVjLC7ZWd54q': '0XN9jRPwMHnW7rvumgfJZOD9CJgVkWYr',
        '5QwRN5qKJTvGKlDTmnf7xwNZcjRmvEy9': 'R2GP6LWBJU1QlnytwGt0B9pytWwAdDYy',
        'eyn5rPPbkfw2KYxH32fG1q58CbLJzM40': 'p2gyqooZnS56JWeiDgfmOy1VugOQEBXn',
        '3BABn3b5RfPJGDwilbHe7l82uBoR05Am': '7OYZG7KMVhbPdKJS3xcWEN3AuDlLNmXj',
        'xA5zNGXD3HrmqMlF6OS5pdMDuZO7RJ4w': 'yY5DAm6r1IOLE3BCVMFveEMAcqnx3r29',
        'g43PgW3JZfml7o6fDEURL1ErCdeD8zyK': 'RX3aQn1zrS4Nr6whDgCGLv9WSbxEKo2V',
        'lAqp8WbGgiG6D8LTKJcg3O72CDdre1Qx': 'O2pnm6473HNJjpKuVosd3vVeh975yrX5',
        'wyJbYEDxKSdbkJ6S6RhW8meou82aqRy8': 'M2wPm7EgRSpQGlAh70CedD4ruzQGdKYy',
        'M4lgW28nLCe0PVdtaXszVXq0SeRVqzA9': 'n2zmJvg4jHv3G0ETNgiwW51LcveWOZ8e',
        '5Qw3OVvp9FvGKlDTmOC7xwNZcjRmvEQ9': 'R2GzDdml9F1Qlnytw9s0B9pytWwAdD8y',
        'vy8a98X7zCwrRqbHrLUjYzwDiK2b70Qb': 'K8lVwzyjZiBpnAaSGeUmnAgxuGOBxmY0',
        'g4eGjJLLoiqRD3Pf9oT5O03LuNbLRDQp': '6XqD59zzpfN4EwQuaGt67qNpSyRBlnYy',
        'g43OPp9boIml7o6fDOIRL1ErCdeD8z4K': 'RX33alNB4s4Nr6whDPUGLv9WSbxEKoXV',
        'xA2ng9OkBcGKzDbTkKsJlx7dUK8R3dA5': 'z2aPnJvzBfObkwGC3vFaPxeBhxoMqZ8K',
        'xyKEgBajZuRr6DEC0Kt7XpD1cnNW9gAv': 'g2ddlEBvRsqdgKaI4jUK9PrgfMexGZ23',
        'BAogww51jIMa2JnH1BcYpXM5F658RNAL': 'rYWDmm0KptlkGv4FGJFMdZmjs9RDE6XR',
        'BAokpg62VtMa2JnH1mHYpXM5F658RNAL': 'rYWryDnlNslkGv4FG4HMdZmjs9RDE62R',
        'a4z1Px5e2hzg0m0iMMCPeanGSkRKWXAg': 'LY9eorNQGUdGW9WuKKf5JGeEik7l1NYQ',
        'kAx69R58kF9nY5YcdecJdl2pFXP53WyX': 'gXyRxELpbfPvLeLSaRil0mp6UEzbZJ8L',
        'BAoY13nwViMa2J2uo2cY6BlETgmdwryL': 'rYWwKzJmNFlkGvGtNoUM9bzwIJVzB1YR',
    }

    _MCP_TO_ACCESS_KEY_TABLE = {
        'qa': 'anvato_mcpqa_demo_web_stage_18b55e00db5a13faa8d03ae6e41f6f5bcb15b922',
        'lin': 'anvato_mcp_lin_web_prod_4c36fbfd4d8d8ecae6488656e21ac6d1ac972749',
        'univison': 'anvato_mcp_univision_web_prod_37fe34850c99a3b5cdb71dab10a417dd5cdecafa',
        'uni': 'anvato_mcp_univision_web_prod_37fe34850c99a3b5cdb71dab10a417dd5cdecafa',
        'dev': 'anvato_mcp_fs2go_web_prod_c7b90a93e171469cdca00a931211a2f556370d0a',
        'sps': 'anvato_mcp_sps_web_prod_54bdc90dd6ba21710e9f7074338365bba28da336',
        'spsstg': 'anvato_mcp_sps_web_prod_54bdc90dd6ba21710e9f7074338365bba28da336',
        'anv': 'anvato_mcp_anv_web_prod_791407490f4c1ef2a4bcb21103e0cb1bcb3352b3',
        'gray': 'anvato_mcp_gray_web_prod_4c10f067c393ed8fc453d3930f8ab2b159973900',
        'hearst': 'anvato_mcp_hearst_web_prod_5356c3de0fc7c90a3727b4863ca7fec3a4524a99',
        'cbs': 'anvato_mcp_cbs_web_prod_02f26581ff80e5bda7aad28226a8d369037f2cbe',
        'telemundo': 'anvato_mcp_telemundo_web_prod_c5278d51ad46fda4b6ca3d0ea44a7846a054f582'
    }

    _TOKEN_GENERATORS = {
        'GXvEgwyJeWem8KCYXfeoHWknwP48Mboj': NFLTokenGenerator,
    }

    _API_KEY = '3hwbSuqqT690uxjNYBktSQpa5ZrpYYR0Iofx7NcJHyA'

    _ANVP_RE = r'<script[^>]+\bdata-anvp\s*=\s*(["\'])(?P<anvp>(?:(?!\1).)+)\1'
    _AUTH_KEY = b'\x31\xc2\x42\x84\x9e\x73\xa0\xce'

    _TESTS = [{
        # from https://www.boston25news.com/news/watch-humpback-whale-breaches-right-next-to-fishing-boat-near-nh/817484874
        'url': 'anvato:8v9BEynrwx8EFLYpgfOWcG1qJqyXKlRM:4465496',
        'info_dict': {
            'id': '4465496',
            'ext': 'mp4',
            'title': 'VIDEO: Humpback whale breaches right next to NH boat',
            'description': 'VIDEO: Humpback whale breaches right next to NH boat. Footage courtesy: Zach Fahey.',
            'duration': 22,
            'timestamp': 1534855680,
            'upload_date': '20180821',
            'uploader': 'ANV',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # from https://sanfrancisco.cbslocal.com/2016/06/17/source-oakland-cop-on-leave-for-having-girlfriend-help-with-police-reports/
        'url': 'anvato:DVzl9QRzox3ZZsP9bNu5Li3X7obQOnqP:3417601',
        'only_matching': True,
    }]

    def __init__(self, *args, **kwargs):
        super(AnvatoIE, self).__init__(*args, **kwargs)
        self.__server_time = None

    def _server_time(self, access_key, video_id):
        if self.__server_time is not None:
            return self.__server_time

        self.__server_time = int(self._download_json(
            self._api_prefix(access_key) + 'server_time?anvack=' + access_key, video_id,
            note='Fetching server time')['server_time'])

        return self.__server_time

    def _api_prefix(self, access_key):
        return 'https://tkx2-%s.anvato.net/rest/v2/' % ('prod' if 'prod' in access_key else 'stage')

    def _get_video_json(self, access_key, video_id):
        # See et() in anvplayer.min.js, which is an alias of getVideoJSON()
        video_data_url = self._api_prefix(access_key) + 'mcp/video/%s?anvack=%s' % (video_id, access_key)
        server_time = self._server_time(access_key, video_id)
        input_data = '%d~%s~%s' % (server_time, md5_text(video_data_url), md5_text(server_time))

        auth_secret = intlist_to_bytes(aes_encrypt(
            bytes_to_intlist(input_data[:64]), bytes_to_intlist(self._AUTH_KEY)))

        video_data_url += '&X-Anvato-Adst-Auth=' + base64.b64encode(auth_secret).decode('ascii')
        anvrid = md5_text(time.time() * 1000 * random.random())[:30]
        api = {
            'anvrid': anvrid,
            'anvts': server_time,
        }
        if self._TOKEN_GENERATORS.get(access_key) is not None:
            api['anvstk2'] = self._TOKEN_GENERATORS[access_key].generate(self, access_key, video_id)
        else:
            api['anvstk'] = md5_text('%s|%s|%d|%s' % (
                access_key, anvrid, server_time,
                self._ANVACK_TABLE.get(access_key, self._API_KEY)))

        return self._download_json(
            video_data_url, video_id, transform_source=strip_jsonp,
            data=json.dumps({'api': api}).encode('utf-8'))

    def _get_anvato_videos(self, access_key, video_id):
        video_data = self._get_video_json(access_key, video_id)

        formats = []
        for published_url in video_data['published_urls']:
            video_url = published_url['embed_url']
            media_format = published_url.get('format')
            ext = determine_ext(video_url)

            if ext == 'smil' or media_format == 'smil':
                formats.extend(self._extract_smil_formats(video_url, video_id))
                continue

            tbr = int_or_none(published_url.get('kbps'))
            a_format = {
                'url': video_url,
                'format_id': join_nonempty('http', published_url.get('cdn_name')).lower(),
                'tbr': tbr or None,
            }

            if media_format == 'm3u8' and tbr is not None:
                a_format.update({
                    'format_id': join_nonempty('hls', tbr),
                    'ext': 'mp4',
                })
            elif media_format == 'm3u8-variant' or ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    video_url, video_id, 'mp4', entry_protocol='m3u8_native',
                    m3u8_id='hls', fatal=False))
                continue
            elif ext == 'mp3' or media_format == 'mp3':
                a_format['vcodec'] = 'none'
            else:
                a_format.update({
                    'width': int_or_none(published_url.get('width')),
                    'height': int_or_none(published_url.get('height')),
                })
            formats.append(a_format)

        self._sort_formats(formats)

        subtitles = {}
        for caption in video_data.get('captions', []):
            a_caption = {
                'url': caption['url'],
                'ext': 'tt' if caption.get('format') == 'SMPTE-TT' else None
            }
            subtitles.setdefault(caption['language'], []).append(a_caption)

        return {
            'id': video_id,
            'formats': formats,
            'title': video_data.get('def_title'),
            'description': video_data.get('def_description'),
            'tags': video_data.get('def_tags', '').split(','),
            'categories': video_data.get('categories'),
            'thumbnail': video_data.get('src_image_url') or video_data.get('thumbnail'),
            'timestamp': int_or_none(video_data.get(
                'ts_published') or video_data.get('ts_added')),
            'uploader': video_data.get('mcp_id'),
            'duration': int_or_none(video_data.get('duration')),
            'subtitles': subtitles,
        }

    @staticmethod
    def _extract_urls(ie, webpage, video_id):
        entries = []
        for mobj in re.finditer(AnvatoIE._ANVP_RE, webpage):
            anvplayer_data = ie._parse_json(
                mobj.group('anvp'), video_id, transform_source=unescapeHTML,
                fatal=False)
            if not anvplayer_data:
                continue
            video = anvplayer_data.get('video')
            if not isinstance(video, compat_str) or not video.isdigit():
                continue
            access_key = anvplayer_data.get('accessKey')
            if not access_key:
                mcp = anvplayer_data.get('mcp')
                if mcp:
                    access_key = AnvatoIE._MCP_TO_ACCESS_KEY_TABLE.get(
                        mcp.lower())
            if not access_key:
                continue
            entries.append(ie.url_result(
                'anvato:%s:%s' % (access_key, video), ie=AnvatoIE.ie_key(),
                video_id=video))
        return entries

    def _extract_anvato_videos(self, webpage, video_id):
        anvplayer_data = self._parse_json(
            self._html_search_regex(
                self._ANVP_RE, webpage, 'Anvato player data', group='anvp'),
            video_id)
        return self._get_anvato_videos(
            anvplayer_data['accessKey'], anvplayer_data['video'])

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})
        self._initialize_geo_bypass({
            'countries': smuggled_data.get('geo_countries'),
        })

        mobj = self._match_valid_url(url)
        access_key, video_id = mobj.group('access_key_or_mcp', 'id')
        if access_key not in self._ANVACK_TABLE:
            access_key = self._MCP_TO_ACCESS_KEY_TABLE.get(
                access_key) or access_key
        return self._get_anvato_videos(access_key, video_id)
