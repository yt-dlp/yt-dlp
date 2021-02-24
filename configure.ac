AC_PREREQ([2.71])
AC_INIT(yt-dlp, 2021.02.19, https://github.com/yt-dlp/yt-dlp/issues)
AM_INIT_AUTOMAKE([foreign])

AC_PROG_INSTALL
AC_PROG_MAKE_SET

PKG_CHECK_VAR(bashcompdir, [bash-completion], [completionsdir], ,
  bashcompdir="${prefix}/share/bash-completion/completions")
AC_SUBST(bashcompdir)
PKG_CHECK_VAR(fishcompdir, [fish], [completionsdir], ,
  fishcompdir="${prefix}/share/fish/vendor_completions.d")
AC_SUBST(fishcompdir)

AC_CONFIG_FILES([Makefile
                 docs/Makefile])
AC_OUTPUT
