Function PD_pin_range, snum, raw = raw, angles = ang, radians= rad, span= spn, $
	_extra = _e

;+
; NAME:
;		PD_PIN_RANGE
; VERSION:
;		7.08
; PURPOSE:
;		Evaluates 1D pinhole coverage range.
; CATEGORY:
;		Surface specific.
; CALLING SEQUENCE:
;		PD_PIN_RANGE, SNUM... [,keywords]
; INPUTS:
;	SNUM
;		Single scan number.
; OPTIONAL INPUT PARAMETERS:
;		None.
; KEYWORD PARAMETERS:
;	/RAW														|
;		Switch.  If set, the result is given in pixel units.	|	At most one
;	/ANGLES														|	of these two
;		Switch.  If set the result is given in angle units, 	|	can be used
;		degrees, unless /RADIANS is set.						|
;	/RADIANS
;		Switch.  If set in conjuction with /ANGLES the output is in radian units
;	/SPAN
;		Switch.  If set, the function returns the span between minimum and
;		maximum of the pinhole coverage, as a scalar.  By default a 2-element
;		vector containing the minimum and maximum of the range is returned.
;	_EXTRA
;		A formal keyword, used to transfer additional keywords to embedded
;		routines.  Not to be used directly.
; OUTPUTS:
;		BY default returns the end points of the pinhole coverage as a 2-element
;		vector, in units of Qxy, unless /RAW or /ANGLES is set. If /SPAN is set
;		returns the span between the endpoints as a scalar value.
; OPTIONAL OUTPUT PARAMETERS:
;		None.
; COMMON BLOCKS:
;		SPEC_FILE.  See the routine SPEC_FILE_INFO for description.
; SIDE EFFECTS:
;		None.
; RESTRICTIONS:
;		None.
; PROCEDURE:
;		Straightforward geometry using the parameter stored in the SPEC file.
;		Calls IMG_COO_CONV, SCAN_PD_CENTER and SPEC_FILE_CHECK.  Calls HOW_MANY
;		from MIDL.
;
;		Note:	The geometrical evaluation uses some parameters specific to
;				15IDC.  If used elsewhere, modifications may be needed.
; MODIFICATION HISTORY:
;		Created 25-JUL-2008 by Mati Meron.
;		Modified 25-AUG-2008 by Mati Meron.  Internal changes.
;-

	common spec_file, exs, fildat, n_s, n_m, n_l, n_smax
	on_error, 1
	if keyword_set(rad) then mult = 1. else mult = !radeg

	Spec_file_check, snum, /sing, /pildet, list = wsnum
	cur = fildat.scan[wsnum]

	angs = !dtor*(cur.angs)[0:2]
	s1 = total((cur.sl_val[*,1])[0:1])
	tdist = 1e-3*((cur.g_l)[2] - (cur.g_l)[1])
	rwid = 1e-4*cur.lambda/s1
	beam = sqrt(s1^2 + (tdist*rwid)^2)
	ftp = beam/sin(angs[0])

	lmlp = cur.pdist - cur.pdsdist
	del = ftp/(2*lmlp)
	psi = atan(2*del*sin(angs[2]),1-del^2) < $
	(atan(cur.sl_val[2,5],cur.pdsdist-32)+ atan(cur.sl_val[3,5],cur.pdsdist-32))
	pix = round(cur.pdsdist*psi/fildat.adpix)
	cent = Scan_PD_center(wsnum)
	xpix = cent[0] + pix/2*[-1,1]

	wha = How_many(fir=ang,sec=raw,/nozero,whi=rtyp)
	if rtyp lt 3 then begin
		if rtyp lt 2 then begin
			ypix = [cent[1],cent[1]]
			dist = cur.pdist + cur.g_l[3]*(1/cos(angs[1]) - 1)
			pdist = cur.pdsdist
			coord = Img_coo_conv(xpix, ypix, dist= dist, pdist= pdist, $
			ipix=fildat.adpix, cent=cent, alp=angs[0],bet=angs[1],dth=angs[2],$
			lam= cur.lambda, /xrev, qvals= 1-rtyp,/rad,_extra= _e)
			res = reform(coord[0,*,0])
			res = res(sort(res))
			if rtyp eq 1 then res = mult*res
		endif else res = xpix
	endif else message, "Can't specify RAW and ANG at the same time!'
	if keyword_set(spn) then res = res[1]-res[0]

	return, res
end