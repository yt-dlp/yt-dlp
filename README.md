<div align="center">

[![YT-DLP](https://raw.githubusercontent.com/yt-dlp/yt-dlp/master/.github/banner.svg)](#readme)

[![Release version](https://img.shields.io/github/v/release/yt-dlp/yt-dlp?color=brightgreen&label=Download&style=for-the-badge)](#installation "Kurulum")
[![PyPI](https://img.shields.io/badge/-PyPI-blue.svg?logo=pypi&labelColor=555555&style=for-the-badge)](https://pypi.org/project/yt-dlp "PyPI")
[![Donate](https://img.shields.io/badge/_-Donate-red.svg?logo=githubsponsors&labelColor=555555&style=for-the-badge)](Maintainers.md#maintainers "Bağış")
[![Discord](https://img.shields.io/discord/807245652072857610?color=blue&labelColor=555555&label=&logo=discord&style=for-the-badge)](https://discord.gg/H5MNcFW63r "Discord")
[![Supported Sites](https://img.shields.io/badge/-Supported_Sites-brightgreen.svg?style=for-the-badge)](supportedsites.md "Desteklenen Siteler")
[![License: Unlicense](https://img.shields.io/badge/-Unlicense-blue.svg?style=for-the-badge)](LICENSE "Lisans")
[![CI Status](https://img.shields.io/github/actions/workflow/status/yt-dlp/yt-dlp/core.yml?branch=master&label=Tests&style=for-the-badge)](https://github.com/yt-dlp/yt-dlp/actions "CI Durumu")
[![Commits](https://img.shields.io/github/commit-activity/m/yt-dlp/yt-dlp?label=commits&style=for-the-badge)](https://github.com/yt-dlp/yt-dlp/commits "Commit Geçmişi")
[![Last Commit](https://img.shields.io/github/last-commit/yt-dlp/yt-dlp/master?label=&style=for-the-badge&display_timestamp=committer)](https://github.com/yt-dlp/yt-dlp/pulse/monthly "Son Aktivite")

</div>
yt-dlp, [binlerce siteyi](supportedsites.md) destekleyen, özellik bakımından zengin bir komut satırı ses/video indiricisidir. Proje, şu an aktif olmayan [youtube-dlc](https://github.com/blackjack4494/yt-dlc)'yi temel alan bir [youtube-dl](https://github.com/ytdl-org/youtube-dl) çatalıdır (fork).

* [KURULUM](#installation)
    * [Ayrıntılı talimatlar](https://github.com/yt-dlp/yt-dlp/wiki/Installation)
    * [Sürüm Dosyaları](#release-files)
    * [Güncelleme](#update)
    * [Bağımlılıklar](#dependencies)
    * [Derleme](#compile)
* [KULLANIM VE SEÇENEKLER](#usage-and-options)
    * [Genel Seçenekler](#general-options)
    * [Ağ Seçenekleri](#network-options)
    * [Coğrafi Kısıtlama](#geo-restriction)
    * [Video Seçimi](#video-selection)
    * [İndirme Seçenekleri](#download-options)
    * [Dosya Sistemi Seçenekleri](#filesystem-options)
    * [Küçük Resim (Thumbnail) Seçenekleri](#thumbnail-options)
    * [İnternet Kısayol Seçenekleri](#internet-shortcut-options)
    * [Detay ve Simülasyon Seçenekleri](#verbosity-and-simulation-options)
    * [Geçici Çözümler (Workarounds)](#workarounds)
    * [Video Formatı Seçenekleri](#video-format-options)
    * [Altyazı Seçenekleri](#subtitle-options)
    * [Kimlik Doğrulama Seçenekleri](#authentication-options)
    * [İşlem Sonrası (Post-processing) Seçenekleri](#post-processing-options)
    * [SponsorBlock Seçenekleri](#sponsorblock-options)
    * [Çıkarıcı (Extractor) Seçenekleri](#extractor-options)
    * [Ön Ayar Takma Adları (Preset Aliases)](#preset-aliases)
* [YAPILANDIRMA](#configuration)
    * [Yapılandırma dosyası kodlaması](#configuration-file-encoding)
    * [netrc ile kimlik doğrulama](#authentication-with-netrc)
    * [Ortam değişkenleri (environment variables) hakkında notlar](#notes-about-environment-variables)
* [ÇIKTI ŞABLONU (OUTPUT TEMPLATE)](#output-template)
    * [Çıktı şablonu örnekleri](#output-template-examples)
* [FORMAT SEÇİMİ](#format-selection)
    * [Formatları Filtreleme](#filtering-formats)
    * [Formatları Sıralama](#sorting-formats)
    * [Format Seçimi örnekleri](#format-selection-examples)
* [META VERİ (METADATA) DÜZENLEME](#modifying-metadata)
    * [Meta veri düzenleme örnekleri](#modifying-metadata-examples)
* [ÇIKARICI (EXTRACTOR) ARGÜMANLARI](#extractor-arguments)
* [EKLENTİLER (PLUGINS)](#plugins)
    * [Eklentileri Kurma](#installing-plugins)
    * [Eklenti Geliştirme](#developing-plugins)
* [YT-DLP'Yİ GÖMME (EMBEDDING)](#embedding-yt-dlp)
    * [Gömme örnekleri](#embedding-examples)
* [YOUTUBE-DL'DEN FARKLARI](#changes-from-youtube-dl)
    * [Yeni özellikler](#new-features)
    * [Varsayılan davranışlardaki farklılıklar](#differences-in-default-behavior)
    * [Kullanımdan kaldırılan seçenekler (Deprecated)](#deprecated-options)
* [KATKIDA BULUNMA](CONTRIBUTING.md#contributing-to-yt-dlp)
    * [Hata/Sorun Bildirme (Opening an Issue)](CONTRIBUTING.md#opening-an-issue)
    * [Geliştirici Talimatları](CONTRIBUTING.md#developer-instructions)
* [WIKI](https://github.com/yt-dlp/yt-dlp/wiki)
    * [SSS (FAQ)](https://github.com/yt-dlp/yt-dlp/wiki/FAQ)
# INSTALLATION

[![Windows](https://img.shields.io/badge/-Windows_x64-blue.svg?style=for-the-badge&logo=windows)](https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe)
[![Unix](https://img.shields.io/badge/-Linux/BSD-red.svg?style=for-the-badge&logo=linux)](https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp)
[![MacOS](https://img.shields.io/badge/-MacOS-lightblue.svg?style=for-the-badge&logo=apple)](https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos)
[![PyPI](https://img.shields.io/badge/-PyPI-blue.svg?logo=pypi&labelColor=555555&style=for-the-badge)](https://pypi.org/project/yt-dlp)
[![Source Tarball](https://img.shields.io/badge/-Source_tar-green.svg?style=for-the-badge)](https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.tar.gz)
[![Other variants](https://img.shields.io/badge/-Other-grey.svg?style=for-the-badge)](#release-files)
[![All versions](https://img.shields.io/badge/-All_Versions-lightgrey.svg?style=for-the-badge)](https://github.com/yt-dlp/yt-dlp/releases)
yt-dlp'yi [derlenmiş ikili dosyalar (binaries)](#release-files), [pip](https://pypi.org/project/yt-dlp) veya üçüncü taraf bir paket yöneticisi kullanarak kurabilirsiniz. Ayrıntılı talimatlar için [wiki'ye](https://github.com/yt-dlp/yt-dlp/wiki/Installation) göz atın.


## RELEASE FILES

#### Önerilen

Dosya|Açıklama
:---|:---
[yt-dlp](https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp)|Platformdan bağımsız [zipimport](https://docs.python.org/3/library/zipimport.html) ikili dosyası. Python gerektirir (**Linux/BSD** için önerilir)
[yt-dlp.exe](https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe)|Windows (Win8+) bağımsız x64 ikili dosyası (**Windows** için önerilir)
[yt-dlp_macos](https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos)|Evrensel MacOS (10.15+) bağımsız çalıştırılabilir dosyası (**MacOS** için önerilir)

#### Alternatifler

Dosya|Açıklama
:---|:---
[yt-dlp_linux](https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_linux)|Linux (glibc 2.17+) bağımsız x86_64 ikili dosyası
[yt-dlp_linux.zip](https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_linux.zip)|Paketlenmemiş Linux (glibc 2.17+) x86_64 çalıştırılabilir dosyası (otomatik güncelleme yok)
[yt-dlp_linux_aarch64](https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_linux_aarch64)|Linux (glibc 2.17+) bağımsız aarch64 ikili dosyası
[yt-dlp_linux_aarch64.zip](https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_linux_aarch64.zip)|Paketlenmemiş Linux (glibc 2.17+) aarch64 çalıştırılabilir dosyası (otomatik güncelleme yok)
[yt-dlp_linux_armv7l.zip](https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_linux_armv7l.zip)|Paketlenmemiş Linux (glibc 2.31+) armv7l çalıştırılabilir dosyası (otomatik güncelleme yok)
[yt-dlp_musllinux](https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_musllinux)|Linux (musl 1.2+) bağımsız x86_64 ikili dosyası
[yt-dlp_musllinux.zip](https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_musllinux.zip)|Paketlenmemiş Linux (musl 1.2+) x86_64 çalıştırılabilir dosyası (otomatik güncelleme yok)
[yt-dlp_musllinux_aarch64](https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_musllinux_aarch64)|Linux (musl 1.2+) bağımsız aarch64 ikili dosyası
[yt-dlp_musllinux_aarch64.zip](https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_musllinux_aarch64.zip)|Paketlenmemiş Linux (musl 1.2+) aarch64 çalıştırılabilir dosyası (otomatik güncelleme yok)
[yt-dlp_x86.exe](https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_x86.exe)|Windows (Win8+) bağımsız x86 (32-bit) ikili dosyası
[yt-dlp_win_x86.zip](https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_win_x86.zip)|Paketlenmemiş Windows (Win8+) x86 (32-bit) çalıştırılabilir dosyası (otomatik güncelleme yok)
[yt-dlp_arm64.exe](https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_arm64.exe)|Windows (Win10+) bağımsız ARM64 ikili dosyası
[yt-dlp_win_arm64.zip](https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_win_arm64.zip)|Paketlenmemiş Windows (Win10+) ARM64 çalıştırılabilir dosyası (otomatik güncelleme yok)
[yt-dlp_win.zip](https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_win.zip)|Paketlenmemiş Windows (Win8+) x64 çalıştırılabilir dosyası (otomatik güncelleme yok)
[yt-dlp_macos.zip](https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos.zip)|Paketlenmemiş MacOS (10.15+) çalıştırılabilir dosyası (otomatik güncelleme yok)

#### Diğer (Misc)

Dosya|Açıklama
:---|:---
[yt-dlp.tar.gz](https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.tar.gz)|Kaynak tarball
[SHA2-512SUMS](https://github.com/yt-dlp/yt-dlp/releases/latest/download/SHA2-512SUMS)|GNU tarzı SHA512 özetleri
[SHA2-512SUMS.sig](https://github.com/yt-dlp/yt-dlp/releases/latest/download/SHA2-512SUMS.sig)|SHA512 özetleri için GPG imza dosyası
[SHA2-256SUMS](https://github.com/yt-dlp/yt-dlp/releases/latest/download/SHA2-256SUMS)|GNU tarzı SHA256 özetleri
[SHA2-256SUMS.sig](https://github.com/yt-dlp/yt-dlp/releases/latest/download/SHA2-256SUMS.sig)|SHA256 özetleri için GPG imza dosyası

GPG imzalarını doğrulamak için kullanılabilecek ortak anahtara (public key) [buradan ulaşabilirsiniz](https://github.com/yt-dlp/yt-dlp/blob/master/public.key).
Örnek kullanım:

curl -L https://github.com/yt-dlp/yt-dlp/raw/master/public.key | gpg --import
gpg --verify SHA2-256SUMS.sig SHA2-256SUMS
gpg --verify SHA2-512SUMS.sig SHA2-512SUMS


#### Lisanslama

yt-dlp [Unlicense](LICENSE) altında lisanslanmış olsa da, yayın dosyalarının birçoğu farklı lisanslara sahip diğer projelerden kodlar içerir.

En önemlisi, PyInstaller ile paketlenmiş çalıştırılabilir dosyalar GPLv3+ lisanslı kodlar içerir ve bu nedenle birleştirilmiş çalışma [GPLv3+](https://www.gnu.org/licenses/gpl-3.0.html) altında lisanslanmıştır.

zipimport Unix çalıştırılabilir dosyası (`yt-dlp`), [`meriyah`](https://github.com/meriyah/meriyah) projesinden [ISC](https://github.com/meriyah/meriyah/blob/main/LICENSE.md) lisanslı kod ve [`astring`](https://github.com/davidbonnet/astring) projesinden [MIT](https://github.com/davidbonnet/astring/blob/main/LICENSE) lisanslı kod içerir.

Daha fazla ayrıntı için [THIRD_PARTY_LICENSES.txt](THIRD_PARTY_LICENSES.txt) dosyasına bakın.

Git deposu, kaynak tarball'u (`yt-dlp.tar.gz`), PyPI kaynak dağıtımı ve PyPI derlenmiş dağıtımı (wheel) yalnızca [Unlicense](LICENSE) altında lisanslanmış kodlar içerir.

**Not**: Man sayfaları (manpages), kabuk otomatik tamamlama (shell completion) dosyaları vb. [kaynak tarball](https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.tar.gz) içerisinde mevcuttur.


## UPDATE
[Derlenmiş sürüm dosyalarını](#release-files) kullanıyorsanız güncellemek için `yt-dlp -U` komutunu kullanabilirsiniz.

[Pip ile kurduysanız](https://github.com/yt-dlp/yt-dlp/wiki/Installation#with-pip), programı kurmak için kullandığınız komutun aynısını tekrar çalıştırmanız yeterlidir.

Diğer üçüncü taraf paket yöneticileri için [wiki'ye](https://github.com/yt-dlp/yt-dlp/wiki/Installation#third-party-package-managers) veya kendi belgelerine başvurun.

<a id="update-channels"></a>

Şu anda ikili dosyalar için üç adet yayın kanalı bulunmaktadır: `stable`, `nightly` ve `master`.

* `stable` varsayılan kanaldır ve içerdiği birçok değişiklik `nightly` ve `master` kanallarındaki kullanıcılar tarafından test edilmiştir.
* `nightly` kanalında, projedeki yeni yamaların ve değişikliklerin anlık görüntüsünü sunmak amacıyla her gün gece yarısı (UTC) civarında derleme yapılması planlanmıştır. Bu kanal, yt-dlp'nin **düzenli kullanıcıları için önerilen** kanaldır. `nightly` sürümlerine [yt-dlp/yt-dlp-nightly-builds](https://github.com/yt-dlp/yt-dlp-nightly-builds/releases) adresinden veya `yt-dlp` PyPI paketinin geliştirme sürümleri olarak (pip'in `--pre` bayrağı ile kurulabilir) erişilebilir.
* `master` kanalı, master dalına yapılan her push işleminden sonra derlenen sürümleri içerir. Bu sürümler en yeni düzeltmelere ve eklentilere sahip olacaktır, ancak aynı zamanda gerilemelere (regression) daha yatkın olabilir. Bunlara [yt-dlp/yt-dlp-master-builds](https://github.com/yt-dlp/yt-dlp-master-builds/releases) adresinden erişilebilir.

`--update`/`-U` kullanıldığında, bir sürüm ikili dosyası (binary) yalnızca kendi mevcut kanalı üzerinden güncellenir.
Yeni bir sürüm mevcut olduğunda farklı bir kanala geçmek için `--update-to CHANNEL` kullanılabilir. Bir kanaldan belirli etiketlere (tags) yükseltmek veya düşürmek için `--update-to [CHANNEL@]TAG` de kullanılabilir.

Tamamen farklı bir depodaki kanala güncellemek için `--update-to <repository>` (`<owner>/<repository>`) komutunu da kullanabilirsiniz. Ancak hangi depoya güncellediğiniz konusunda dikkatli olun, farklı depolardaki ikili dosyalar için herhangi bir doğrulama yapılmaz.

Örnek kullanım:

* `yt-dlp --update-to master` -> `master` kanalına geçer ve bu kanalın en son sürümüne günceller.
* `yt-dlp --update-to stable@2023.07.06` -> `stable` kanalındaki `2023.07.06` etiketli sürüme yükseltir/düşürür.
* `yt-dlp --update-to 2023.10.07` -> Eğer mevcut kanalda varsa `2023.10.07` etiketli sürüme yükseltir/düşürür.
* `yt-dlp --update-to example/yt-dlp@2023.09.24` -> `example/yt-dlp` deposundan `2023.09.24` etiketli sürüme yükseltir/düşürür.

**Önemli**: `stable` sürümüyle ilgili bir sorun yaşayan herhangi bir kullanıcı, hata raporu göndermeden önce `nightly` sürümünü kurmalı veya güncellemelidir:

Stable çalıştırılabilir dosyasını/binary'sini nightly sürümüne güncellemek için:

yt-dlp --update-to nightly
Nightly sürümünü pip ile kurmak için:

python -m pip install -U --pre "yt-dlp[default]"


90 günden daha eski bir yt-dlp sürümü çalıştırdığınızda, en son sürüme güncellemenizi öneren bir uyarı mesajı göreceksiniz.
Bu uyarıyı komutunuza veya yapılandırma dosyanıza `--no-update` ekleyerek gizleyebilirsiniz.

## DEPENDENCIES
Python 3.10+ (CPython) ve 3.11+ (PyPy) sürümleri desteklenmektedir. Diğer sürümler ve uygulamalar (implementations) doğru çalışabilir veya çalışmayabilir.

Diğer tüm bağımlılıklar isteğe bağlı olmakla birlikte, `ffmpeg`, `ffprobe`, `yt-dlp-ejs` ve desteklenen bir JavaScript çalışma zamanı/motoru (runtime/engine) kullanılması şiddetle tavsiye edilir.

### Şiddetle Tavsiye Edilenler

* [**ffmpeg** ve **ffprobe**](https://www.ffmpeg.org) - Ayrı video ve ses dosyalarını [birleştirmek](#format-selection) ve çeşitli [işlem sonrası (post-processing)](#post-processing-options) görevleri için gereklidir. Lisans, [yapılan derlemeye bağlıdır](https://www.ffmpeg.org/legal.html).

    ffmpeg içinde, yt-dlp ile birlikte kullanıldığında çeşitli sorunlara neden olan bazı hatalar (bugs) vardır. ffmpeg çok önemli bir bağımlılık olduğu için, bu sorunların bazılarını çözen yamalara sahip [özel derlemeleri (custom builds)](https://github.com/yt-dlp/FFmpeg-Builds#ffmpeg-static-auto-builds), [yt-dlp/FFmpeg-Builds](https://github.com/yt-dlp/FFmpeg-Builds) deposunda sağlıyoruz. Bu derlemeler tarafından çözülen belirli sorunlarla ilgili ayrıntılar için [oku dosyasına (readme)](https://github.com/yt-dlp/FFmpeg-Builds#patches-applied) göz atın.

    **Önemli**: İhtiyacınız olan şey ffmpeg *ikili dosyasıdır (binary)*, aynı isme sahip [Python paketi](https://pypi.org/project/ffmpeg) **DEĞİLDİR**.

* [**yt-dlp-ejs**](https://github.com/yt-dlp/ejs) - Tam YouTube desteği için gereklidir. [Unlicense](https://github.com/yt-dlp/ejs/blob/main/LICENSE) altında lisanslanmıştır, [MIT](https://github.com/davidbonnet/astring/blob/main/LICENSE) ve [ISC](https://github.com/meriyah/meriyah/blob/main/LICENSE.md) bileşenlerini barındırır.

    yt-dlp-ejs'yi çalıştırmak için [**deno**](https://deno.land) (önerilir), [**node.js**](https://nodejs.org), [**bun**](https://bun.sh) veya [**QuickJS**](https://bellard.org/quickjs/) gibi bir JavaScript çalışma zamanı/motoru (runtime/engine) da gereklidir. Bkz. [wiki](https://github.com/yt-dlp/yt-dlp/wiki/EJS).

### Ağ İşlemleri (Networking)
* [**certifi**](https://github.com/certifi/python-certifi)\* - Mozilla'nın kök sertifika (root certificate) paketini sağlar. [MPLv2](https://github.com/certifi/python-certifi/blob/master/LICENSE) altında lisanslanmıştır.
* [**brotli**](https://github.com/google/brotli)\* veya [**brotlicffi**](https://github.com/python-hyper/brotlicffi) - [Brotli](https://en.wikipedia.org/wiki/Brotli) içerik kodlama desteği. Her ikisi de MIT <sup>[1](https://github.com/google/brotli/blob/master/LICENSE) [2](https://github.com/python-hyper/brotlicffi/blob/master/LICENSE) </sup> altında lisanslanmıştır.
* [**websockets**](https://github.com/aaugustin/websockets)\* - Websocket üzerinden indirme yapmak için. [BSD-3-Clause](https://github.com/aaugustin/websockets/blob/main/LICENSE) altında lisanslanmıştır.
* [**requests**](https://github.com/psf/requests)\* - HTTP kütüphanesi. HTTPS proxy ve kalıcı bağlantı (persistent connections) desteği içindir. [Apache-2.0](https://github.com/psf/requests/blob/main/LICENSE) altında lisanslanmıştır.

#### Kimliğe Bürünme (Impersonation)

Aşağıdakiler, tarayıcı isteklerini taklit etme (impersonating) desteği sağlar. Bu durum, TLS parmak izi (fingerprinting) kullanan bazı siteler için gerekli olabilir.

* [**curl_cffi**](https://github.com/lexiforest/curl_cffi) (önerilen) - [curl-impersonate](https://github.com/lexiforest/curl-impersonate) için Python bağlayıcısı (binding). Chrome, Edge ve Safari için taklit (impersonation) hedefleri sağlar. [MIT](https://github.com/lexiforest/curl_cffi/blob/main/LICENSE) altında lisanslanmıştır.
  * `curl-cffi` ekstrası ile kurulabilir, örn: `pip install "yt-dlp[default,curl-cffi]"`
  * Şu anda `yt-dlp` (Unix zipimport binary), `yt-dlp_x86` (Windows 32-bit) ve `yt-dlp_musllinux_aarch64` *hariç* çoğu derlemeye dâhildir.

### Meta Veri (Metadata)

* [**mutagen**](https://github.com/quodlibet/mutagen)\* - Belirli formatlarda `--embed-thumbnail` kullanımı içindir. [GPLv2+](https://github.com/quodlibet/mutagen/blob/master/COPYING) altında lisanslanmıştır.
* [**AtomicParsley**](https://github.com/wez/atomicparsley) - `mutagen`/`ffmpeg` işlemez duruma geldiğinde `mp4`/`m4a` dosyalarında `--embed-thumbnail` kullanımı içindir. [GPLv2+](https://github.com/wez/atomicparsley/blob/master/COPYING) altında lisanslanmıştır.
* [**xattr**](https://github.com/xattr/xattr), [**pyxattr**](https://github.com/iustin/pyxattr) veya [**setfattr**](http://savannah.nongnu.org/projects/attr) - **Mac** ve **BSD** sistemlerinde xattr meta verisi yazmak (`--xattrs`) içindir. Sırasıyla [MIT](https://github.com/xattr/xattr/blob/master/LICENSE.txt), [LGPL2.1](https://github.com/iustin/pyxattr/blob/master/COPYING) ve [GPLv2+](http://git.savannah.nongnu.org/cgit/attr.git/tree/doc/COPYING) altında lisanslanmıştır.

### Çeşitli (Misc)

* [**pycryptodomex**](https://github.com/Legrandin/pycryptodome)\* - AES-128 HLS akışlarının (streams) şifresini çözmek (decrypting) ve diğer çeşitli veriler içindir. [BSD-2-Clause](https://github.com/Legrandin/pycryptodome/blob/master/LICENSE.rst) altında lisanslanmıştır.
* [**phantomjs**](https://github.com/ariya/phantomjs) - JavaScript'in çalıştırılması gereken bazı çıkarıcılarda (extractors) kullanılır. Artık YouTube için kullanılmamaktadır. Yakın gelecekte kullanımdan kaldırılacaktır. [BSD-3-Clause](https://github.com/ariya/phantomjs/blob/master/LICENSE.BSD) altında lisanslanmıştır.
* [**secretstorage**](https://github.com/mitya57/secretstorage)\* - **Linux** üzerinde **Chromium** tabanlı tarayıcıların çerezlerinin şifresini çözerken **Gnome** anahtarlığına (keyring) erişmek maksadıyla `--cookies-from-browser` kullanımı içindir. [BSD-3-Clause](https://github.com/mitya57/secretstorage/blob/master/LICENSE) altında lisanslanmıştır.
* `--downloader` ile kullanmak isteyebileceğiniz herhangi bir harici indirici.

### Kullanımdan Kaldırılanlar (Deprecated)

* [**rtmpdump**](http://rtmpdump.mplayerhq.hu) - `rtmp` akışlarını (streams) indirmek içindir. Bunun yerine `--downloader ffmpeg` bayrağı ile ffmpeg kullanılabilir. [GPLv2+](http://rtmpdump.mplayerhq.hu) altında lisanslanmıştır.
* [**mplayer**](http://mplayerhq.hu/design7/info.html) veya [**mpv**](https://mpv.io) - `rstp`/`mms` akışlarını indirmek içindir. Bunun yerine `--downloader ffmpeg` bayrağı ile ffmpeg kullanılabilir. [GPLv2+](https://github.com/mpv-player/mpv/blob/master/Copyright) altında lisanslanmıştır.

Bağımlılıkları kullanmak veya yeniden dağıtmak için ilgili lisanslama koşullarını kabul etmeniz gerekir.

Bağımsız yayın ikili dosyaları (standalone release binaries), Python yorumlayıcısı (interpreter) ve **\*** ile işaretlenmiş paketler dâhil edilerek derlenmiştir.

Giriştiğiniz bir görev için gerekli bağımlılıklara sahip değilseniz, yt-dlp sizi uyaracaktır. Mevcut tüm bağımlılıklar `--verbose` çıktısının en üstünde görülebilir.


## COMPILE

### Bağımsız PyInstaller Derlemeleri
Bağımsız çalıştırılabilir dosyayı oluşturmak için Python ve `pyinstaller`'a (ayrıca gerekliyse yt-dlp'nin [isteğe bağlı bağımlılıklarından](#dependencies) herhangi birine) sahip olmanız gerekir. Çalıştırılabilir dosya, kullanılan Python ile aynı CPU mimarisi için derlenecektir.

Aşağıdaki komutları çalıştırabilirsiniz:

python devscripts/install_deps.py --include-extra pyinstaller
python devscripts/make_lazy_extractors.py
python -m bundle.pyinstaller


Bazı sistemlerde `python` yerine `py` veya `python3` kullanmanız gerekebilir.

`python -m bundle.pyinstaller`, `pyinstaller`'a aktarılabilecek `--onefile/-F` veya `--onedir/-D` gibi herhangi bir argümanı kabul eder; bu konu [burada daha ayrıntılı olarak belgelenmiştir](https://pyinstaller.org/en/stable/usage.html#what-to-generate).

**Not**: 4.4'ten düşük Pyinstaller sürümleri, sanal ortam (virtual environment) kullanmadan Windows Mağazası üzerinden kurulan Python'u [desteklemez](https://github.com/pyinstaller/pyinstaller#requirements-and-tested-platforms).

**Önemli**: `python -m bundle.pyinstaller` kullanmak **yerine** doğrudan `pyinstaller` komutunu çalıştırmak resmi olarak **desteklenmez**. Bu yöntem düzgün çalışabilir de çalışmayabilir de.

### Platformdan Bağımsız İkili Dosya (UNIX)
`python` (3.10+), `zip`, `make` (GNU), `pandoc`\* ve `pytest`\* derleme araçlarına (build tools) ihtiyacınız olacak.

Bunları kurduktan sonra sadece `make` komutunu çalıştırmanız yeterlidir.

Ek dosyaların hiçbirini güncellemeden yalnızca ikili dosyayı derlemek için `make yt-dlp` komutunu da çalıştırabilirsiniz. (**\*** ile işaretlenmiş derleme araçları bu işlem için gerekli değildir).

### İlgili script'ler

* **`devscripts/install_deps.py`** - yt-dlp için bağımlılıkları yükler.
* **`devscripts/update-version.py`** - Sürüm numarasını mevcut tarihe göre günceller.
* **`devscripts/set-variant.py`** - Çalıştırılabilir dosyanın derleme varyantını (build variant) ayarlar.
* **`devscripts/make_changelog.py`** - Kısa commit mesajlarını kullanarak bir markdown değişiklik günlüğü (changelog) oluşturur ve `CONTRIBUTORS` dosyasını günceller.
* **`devscripts/make_lazy_extractors.py`** - Tembel (lazy) çıkarıcılar (extractors) oluşturur. İkili dosyaları (herhangi bir varyant) derlemeden önce bunu çalıştırmak, başlangıç (startup) performanslarını artıracaktır. Tembel çıkarıcı yüklemesini zorla devre dışı bırakmak için `YTDLP_NO_LAZY_EXTRACTORS` ortam değişkenini boş olmayan bir değere ayarlayın.

Not: Daha fazla bilgi için bu script'lerin `--help` ekranına bakın.

### Projeyi çatallamak (Forking)
Projeyi GitHub üzerinde çatallarsanız (fork), seçilen sürümü (sürümleri) yapı (artifact) olarak otomatik bir şekilde derlemek için kendi çatalınızın [derleme iş akışını (build workflow)](.github/workflows/build.yml) çalıştırabilirsiniz. Alternatif olarak, tam (ön) sürümler oluşturmak için [yayın iş akışını (release workflow)](.github/workflows/release.yml) çalıştırabilir veya [gecelik (nightly) iş akışını](.github/workflows/release-nightly.yml) etkinleştirebilirsiniz.

# USAGE AND OPTIONS

yt-dlp [OPTIONS] [--] URL [URL...]

İpucu: Anahtar kelimelere göre arama yapmak için `CTRL`+`F` (veya `Command`+`F`) kısayolunu kullanın.
## General Options (Genel Seçenekler):
    -h, --help                          Bu yardım metnini yazdırır ve çıkar
    --version                           Program sürümünü yazdırır ve çıkar
    -U, --update                        Bu programı en son sürüme günceller
    --no-update                         Güncellemeleri kontrol etmez (varsayılan)
    --update-to [CHANNEL]@[TAG]         Belirli bir sürüme yükseltir/düşürür.
                                        CHANNEL bir depo da olabilir. Atlanırsa
                                        CHANNEL ve TAG sırasıyla "stable" ve "latest" 
                                        olarak varsayılır; Ayrıntılar için "UPDATE"
                                        bölümüne bakın. Desteklenen kanallar: stable,
                                        nightly, master
    -i, --ignore-errors                 İndirme ve işlem sonrası (postprocessing)
                                        hatalarını yoksayar. İşlem sonrası aşama 
                                        başarısız olsa bile indirme başarılı
                                        kabul edilir
    --no-abort-on-error                 İndirme hatalarında bir sonraki videoya devam eder;
                                        örn. bir oynatma listesindeki (playlist)
                                        kullanılamayan videoları atlamak için (varsayılan)
    --abort-on-error                    Bir hata oluşursa sonraki videoların indirilmesini 
                                        iptal eder (Takma Ad/Alias: --no-ignore-errors)
    --list-extractors                   Desteklenen tüm çıkarıcıları (extractors)
                                        listeler ve çıkar
    --extractor-descriptions            Desteklenen tüm çıkarıcıların açıklamalarını
                                        çıktı olarak verir ve çıkar
    --use-extractors NAMES              Kullanılacak çıkarıcı adları (virgülle ayrılmış).
                                        Ayrıca düzenli ifadeler (regex), "all", "default"
                                        ve "end" (URL eşleşmesini sonlandır) de
                                        kullanabilirsiniz; örn. --ies "holodex.*,end,youtube".
                                        Hariç tutmak için ismin başına "-" ekleyin, 
                                        örn. --ies default,-generic. Çıkarıcı adlarının
                                        bir listesi için --list-extractors kullanın.
                                        (Takma Ad/Alias: --ies)
    --default-search PREFIX             Nitelenmemiş (unqualified) URL'ler için bu 
                                        önekleri (prefix) kullanır. Örn. "gvsearch2:python"
                                        "python" arama terimi için google videolarından
                                        iki video indirir. yt-dlp'nin tahminde
                                        bulunmasına izin vermek için "auto" değerini
                                        kullanın (tahmin ederken bir uyarı vermek
                                        için "auto_warning"). "error" yalnızca bir 
                                        hata fırlatır. Varsayılan "fixup_error"
                                        değeri kırık URL'leri onarır ancak bu mümkün 
                                        değilse arama yapmak yerine bir hata verir
    --ignore-config                     --config-locations'a verilenler dışında
                                        başka hiçbir yapılandırma dosyasını yüklemez.
                                        Geriye dönük uyumluluk için, eğer bu seçenek
                                        sistem yapılandırma dosyasının (config) içinde
                                        bulunursa, kullanıcı yapılandırması yüklenmez.
                                        (Takma Ad/Alias: --no-config)
    --no-config-locations               Hiçbir özel yapılandırma dosyasını yüklemez
                                        (varsayılan). Bir yapılandırma dosyası içinde 
                                        verildiğinde, mevcut dosyada tanımlanan 
                                        önceki tüm --config-locations komutlarını 
                                        görmezden gelir
    --config-locations PATH             Ana yapılandırma dosyasının konumu; config'in
                                        kendisine giden yol ya da onu içeren dizindir
                                        (stdin için "-"). Birden çok kez ve
                                        başka yapılandırma dosyalarının içinde
                                        kullanılabilir
    --plugin-dirs DIR                   Eklentileri (plugins) aramak için ek bir dizinin 
                                        yolu. Bu seçenek, birden fazla dizin eklemek için 
                                        birden çok kez kullanılabilir. Varsayılan eklenti 
                                        dizinlerinde arama yapmak için "default" kullanın 
                                        (varsayılan)
    --no-plugin-dirs                    Varsayılanlar ve önceki --plugin-dirs tarafından
                                        sağlananlar dâhil aranacak eklenti dizinlerini 
                                        temizler
    --js-runtimes RUNTIME[:PATH]        Etkinleştirilecek ek JavaScript çalışma zamanı,
                                        çalışma zamanı için isteğe bağlı bir konumla 
                                        birlikte (ikili dosyanın (binary) kendi yolu veya 
                                        içeren dizini). Bu seçenek birden fazla çalışma 
                                        zamanı etkinleştirmek için birden çok kez 
                                        kullanılabilir. Desteklenen çalışma zamanları
                                        (öncelik sırasına göre, en yüksekten en düşüğe):
                                        deno, node, quickjs, bun. Varsayılan olarak yalnızca
                                        "deno" etkindir. Hem etkin hem de kullanılabilir
                                        olan en yüksek öncelikli çalışma zamanı
                                        kullanılacaktır. "deno" mevcut olduğunda 
                                        daha düşük öncelikli bir çalışma zamanı 
                                        kullanmak için, diğer çalışma zamanları 
                                        etkinleştirilmeden önce --no-js-runtimes 
                                        komutunun geçirilmesi gerekir
    --no-js-runtimes                    Varsayılanlar ve önceki --js-runtimes tarafından
                                        sağlananlar dâhil etkinleştirilecek JavaScript 
                                        çalışma zamanlarını temizler
    --remote-components COMPONENT       Gerektiğinde yt-dlp'nin çekmesine izin verilecek
                                        uzak bileşenler (remote components). Resmi bir 
                                        çalıştırılabilir dosya kullanıyorsanız veya 
                                        yt-dlp-ejs paketinin gerekli sürümü kuruluysa,
                                        şu anda bu seçeneğe ihtiyaç yoktur. Birden fazla
                                        bileşene izin vermek için bu seçeneği birden
                                        çok kez kullanabilirsiniz. Desteklenen değerler:
                                        ejs:npm (npm'den alınan harici JavaScript
                                        bileşenleri), ejs:github (yt-dlp-ejs GitHub'dan
                                        alınan harici JavaScript bileşenleri). 
                                        Varsayılan olarak, hiçbir uzak bileşene izin verilmez
    --no-remote-components              --remote-components veya varsayılanlar 
                                        tarafından önceden izin verilenler dâhil,
                                        tüm uzak bileşenlerin çekilmesini (fetching)
                                        engeller.
    --flat-playlist                     Bir oynatma listesinin (playlist) URL sonuç 
                                        girdilerini çıkarmaz (extract); bazı girdi 
                                        meta verileri (metadata) eksik olabilir ve 
                                        indirme işlemi atlanabilir
    --no-flat-playlist                  Bir oynatma listesinin (playlist) videolarını 
                                        tamamen çıkarır (varsayılan)
    --live-from-start                   Canlı yayınları (livestreams) baştan itibaren
                                        indirir. Şu anda deneyseldir ve yalnızca
                                        YouTube, Twitch ve TVer için desteklenmektedir
    --no-live-from-start                Canlı yayınları mevcut (güncel) zamandan
                                        itibaren indirir (varsayılan)
    --wait-for-video MIN[-MAX]          Zamanlanmış yayınların (scheduled streams)
                                        kullanılabilir hale gelmesini bekler. Yeniden 
                                        denemeler arasında beklenecek minimum saniye
                                        sayısını (veya aralığı) iletin
    --no-wait-for-video                 Zamanlanmış yayınlar (scheduled streams) için
                                        beklemez (varsayılan)
    --mark-watched                      Videoları izlendi olarak işaretler (--simulate 
                                        ile kullanılsa dahi)
    --no-mark-watched                   Videoları izlendi olarak işaretlemez (varsayılan)
    --color [STREAM:]POLICY             Çıktıda renk kodlarının yayılıp yayılmayacağını 
                                        belirler; tercihen ayarın uygulanacağı STREAM 
                                        (stdout veya stderr) önekiyle kullanılabilir. 
                                        Değerlerden biri şunlar olabilir: "always", 
                                        "auto" (varsayılan), "never", veya "no_color"
                                        (renk içermeyen terminal dizileri kullan).
                                        Bunu belirlemek için "auto-tty" veya "no_color-tty"
                                        kullanın.
