# Copyright 1999-2007 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: /opt/data/files/travis/cvsroot/eyeD3/etc/gentoo/Attic/eyeD3-0.6.12.ebuild,v 1.1.2.1 2007/02/18 23:34:46 travis Exp $

NEED_PYTHON=2.5

inherit distutils

DESCRIPTION="Module for manipulating ID3 (v1 + v2) tags in Python"
HOMEPAGE="http://eyed3.nicfit.net/"
SRC_URI="http://eyed3.nicfit.net/releases/${P}.tar.gz"
IUSE=""
LICENSE="GPL-2"
SLOT="0"
KEYWORDS="~amd64 ~ia64 ~ppc ~sparc ~x86"

src_compile() {
	econf || die
	distutils_src_compile || die
}

src_install() {
	make DESTDIR="${D}" all install || die

	dodoc NEWS TODO
	dohtml README.html
}
