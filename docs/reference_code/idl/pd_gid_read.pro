Function PD_GID_read, sp_0, sp_1, sp_2, sp_3, sp_4, sp_5, sp_6, sp_7, $
	hroi = hroi, vroi = vroi, patch_range = ptr, angles = ang, $
	signed = sgn, relaxed = rel, verbose = vrb, title = tit, _extra = _e

;+
; NAME:
;		PD_GID_READ
; VERSION:
;		7.0
; PURPOSE:
;		Reads a set of PD scans, integrates each horizontally and joins them
;		into a 2D image.
; CATEGORY:
;		Surface specific.
; CALLING SEQUENCE:
;		Result = PD_GID_READ( SP_0, ..., [,keywords])
; INPUTS:
;	SP_0, SP_1, SP_2, SP_3, SP_4, SP_5, SP_6, SP_7
;		List of SPEC PD scans, provided in any form that is acceptable by
;		SCAN_LIST_VER (note, each scan may contain multiple PD files).  If more
;		than one scan is provided, PD_GID_READ will attempt patching in the
;		horizontal direction.
; OPTIONAL INPUT PARAMETERS:
;		None.
; KEYWORD PARAMETERS:
;	HROI
;		Two element vector defining horizontal region of interest, in *pixels*.
;	VROI
;		Two element vector defining vertical region of interest, in *pixels*.
;	PATCH_RANGE
;		The range of channels to use in patching (only when more than one data
;		set is present).  Note that PATCH_RANGE values are taken as original
;		values, before VROI is applied.
;	/ANGLES
;		Switch.  If set the coordinates of the image are the angles DTHETA (for
;		horizontal) and BETA for vertical, instead of Q_xy and Q_z.
;	/SIGNED
;		Switch.  If set, Q_xy is multiplied by the sign of the DTH angle.
;		/SIGNED has no effect when /ANGLES is set.
;	/RELAXED
;		Switch.  If set, the internal transformation from angles to Q-values is
;		unconstrained.  By default it is constrained to the internal data
;		region, to avoid edge inaccuracies.
;	/VERBOSE
;		Switch.  If set and PATCH_RANGE is provided, the Q_z patching range is
;		printed to the screen (only when more than one group of scans is used).
;	TITLE
;		Optional output (and input), see below.
;	_EXTRA
;		A formal keyword, used to transfer additional keywords to embedded
;		routines.  This includes (among others) the following keywords,
;		affecting data readout:
;
;			/BAD
;				Switch.  If set, faulty (very high count rate) pixels are
;				removed from the data.
;			/NORM
;				Switch.  If set, the data is normalized to monitor counts.
;
;		See SCAN_PD_READ for more details.
; OUTPUTS:
;		Usually returns a 3D array of dimensions [4,NP,NL] (where NP is the
;		number of PD files used and NL is the long dimension of the PD) such
;		that
;			Result[0,*,*] = Q_xy coordinates of the image.
;			Result[1,*,*] = Q_z coordinates of the image.
;			Result[2,*,*] = The image itself.
;			Result[3,*,*] = The statistical errors of the image data.
;
;		In the special case when only a single scan is present (i.e. NP = 1)
;		returns a 2D array of dimensions [3,NL] such that
;			Result[0,*] = Q_z coordinates of the scan.
;			Result[1,*] = The scan data itself.
;			Result[2,*] = The statistical errors of the data.
;
;		However, see /ANGLES above for alternative coordinates.
;
;		Note that NL may be lower, if VROI is used.
; OPTIONAL OUTPUT PARAMETERS:
;	TITLE
;		If provided, returns the same, else returns a character scalar, made of
;		the file name and the scan numbers, to be used as title for plots.
; COMMON BLOCKS:
;		SPEC_FILE.  See the routine SPEC_FILE_INFO for description.
; SIDE EFFECTS:
;		None.
; RESTRICTIONS:
;		1)  The scan list provided must include only valid PD scans.
;		2)	The value of LAMBDA must be constant for all the scans and equal
;			the calibration value (to within 1e-3 relative).
;		3)  The values of ALPHA and BETA must be constant for all the scans
;			(to within 1e-3).
; PROCEDURE:
;		Reads the data, evaluates Q_z and Q_xy using calibration values, then
;		translates the Q values to rectalinear coordinates and interpolates
;		the data using triangulation.
;		Calls SCAN_FIELD READ, SCAN_JOIN, SCAN_ORDER, SCAN_PAR_READ,
;		SCAN_PD_COMB and SPEC_FILE_INFO from SPEC.  Calls IMG_TRIG.
;		Also calls ARREQ, ARRPACK, DEFAULT, ISNUM, RANGE_PROC, SIGN and
;		WHERINSTRUCT from MIDL.
; MODIFICATION HISTORY:
;		Created 1-NOV-2007 by Mati Meron, based on LD_READ.
;		Modified 10-APR-2008 by Mati Meron.  Internal changes.
;-

	common spec_file, exs, fildat, n_s, n_m, n_l, n_smax
	on_error, 1

	nmax = 8
	warn = 'Missing or non-constant '
	dnam = ['Pdist','PDxc','Lambda','G_L']
	wdnam = ['detector distance.','specular channel.','lambda','G_L']
	pnam = ['In_Rot','Out_Rot']
	wpnam = ['Alpha','Beta']

	Spec_file_info, /check, _extra = _e
	dum = (Wherinstruct('new',_e))[0]
	if dum ge 0 then _e.(dum) = 0

	tem = Arrpack(sp_0,sp_1,sp_2,sp_3,sp_4,sp_5,sp_6,sp_7,count=cnt)
	if cnt gt 0 then begin
		snum = Range_proc(tem,/uni)
		n = n_elements(snum)
		if n gt nmax then message, $
		'At most ' + string(nmax,form='(i2)') + ' scans allowed!'
	endif else message, 'Missing inputs!'

	if n gt 1 then begin
		pdnam =  strcompress('pd_' + sindgen(nmax),/remove)
		dtnam =  strcompress('dt_' + sindgen(nmax),/remove)
		zinam =  strcompress('zi_' + sindgen(nmax),/remove)
		opdnam =  strcompress('opd_' + sindgen(nmax),/remove)
		odtnam =  strcompress('odt_' + sindgen(nmax),/remove)
		ozinam =  strcompress('ozi_' + sindgen(nmax),/remove)

		ssnum = string(snum)
		nxs = lonarr(n)
		si = sindgen(n)
		acom = '= Scan_pd_comb('
		bcom = ',ori=1,hroi=hroi,vroi=vroi,dth=ddth,_extra=_e)'
		if Isnum(ptr) then begin
			if Isnum(vroi) then begin
				lo = min(vroi,max=hi)
				wptr = (lo > ptr < hi) - lo
			endif else wptr = ptr > 0
		endif
		case n_elements(wptr) of
			0	:	begin
						fran = '[*,*,0]'
						sran = '[*,*,1]'
					end
			1	:	begin
						dum = strcompress(string(wptr),/rem)
						fran = '[*,'+dum+':*,0]'
						sran = '[*,'+dum+':*,1]'
					end
			2	:	begin
						wptr = wptr(sort(wptr))
						dum = strcompress(strjoin(string(wptr),':'),/rem)
						fran = '[*,'+dum+',0]'
						sran = '[*,'+dum+',1]'
					end
			else:	message, 'Patch range can have at most 2 elements!'
		endcase

		for i = 0, n-1 do begin
			dum = execute(pdnam[i] + acom + ssnum[i] + bcom)
			dum = execute(dtnam[i] + ' = ddth')
			nxs[i] = n_elements(ddth)
			s = sort(ddth)
			if not Arreq(s,lindgen(nxs[i])) then begin
				dum = execute(pdnam[i] + '=' + pdnam[i] + '[s,*,*]')
				dum = execute(dtnam[i] + '=' + dtnam[i] + '[s]')
			endif
			dum = execute('zint = total((' + pdnam[i] + ')'+fran+',2)')
			dum = execute('ezint = total((' + pdnam[i] + ')'+sran+'^2,2)')
			tem = fltarr(3,nxs[i])
			tem[0,*] = ddth
			tem[1,*] = zint
			tem[2,*] = sqrt(ezint)
			dum = execute(zinam[i] + ' = tem')
		endfor

		dum = execute('j = Scan_order(' + strjoin(zinam,',') + ')')
		nxs = nxs[j]
		snum = snum[j]
		for i = 0, n-1 do begin
			dum = execute(opdnam[i] + '=' + pdnam[j[i]])
			dum = execute(odtnam[i] + '=' + dtnam[j[i]])
			dum = execute(ozinam[i] + '=' + zinam[j[i]])
		endfor

		bcom = ',/relaxed,fac=mfac,over=ovl,_extra = _e)'
		dum = execute('zicomb = Scan_join(' + strjoin(ozinam,',') + bcom)
		ddth = reform(zicomb[0,*])
		xsiz = total(nxs-ovl)
		zsiz = (size(opd_0))[2]
		pdat = findgen(xsiz,zsiz,2)
		mflis = findgen(xsiz)
		lo = (shift(total([0,nxs] - [ovl,0],/cum),1))[1:*]
		hi = lo + nxs - 1
		slo = string(lo)
		shi = string(hi)
		smfac = string(mfac)
		for i = 0, n-1 do begin
			dum = $
			execute('pdat['+slo[i]+':'+shi[i]+',*,*]='+ smfac[i]+ '*'+opdnam[i])
			dum = execute('mflis['+slo[i]+':'+shi[i]+'] = mfac['+si[i]+']')
		endfor
		siz = size(pdat)
	endif else begin
		pdat = Scan_PD_comb(snum,ori=1,hroi=hroi,vroi=vroi,dth=ddth,_extra=_e)
		s = sort(ddth)
		if not Arreq(s,lindgen(n_elements(ddth))) then begin
			pdat = pdat[s,*,*]
			ddth = ddth[s]
		endif
		siz = size(pdat)
		mflis = replicate(1.,siz[1])
	endelse

	tit=Default(tit,strcompress(fildat.name+'  S# '+strjoin(string(snum),',')))

	pix = fildat.adpix
	dist = (Scan_field_read(snum,dnam[0],/const,cfl=cfl))[0]
	if not cfl then message, warn + wdnam[0]
	ns = (Scan_field_read(snum,dnam[1],/const,cfl=cfl))[0]
	if not cfl then message, warn + wdnam[2]
	lam = (Scan_field_read(snum,dnam[2],/const,tol=1e-3,cfl=cfl))[0]
	if not cfl then message, warn + wdnam[3]
	gl3 = Scan_field_read(snum,dnam[3],/const,tol=1.,cfl=cfl)
	if Arreq(cfl,[1,1,1,1]) then gl3 = gl3[3] else message, warn + wdnam[3]

	talp = !dtor*(Scan_par_read(snum,pnam[0],/const,tol=1e-3,cfl=cfl))[0]
	if not cfl then message, warn + wpnam[0]
	tbet = !dtor*(Scan_par_read(snum,pnam[1],/const,tol=1e-3,cfl=cfl))[0]
	if not cfl then message, warn + wpnam[1]
	tdth = !dtor*ddth

	wdist = dist + gl3*(1/cos(tbet) - 1)
	n = lindgen(siz[2]) + (Default(vroi,0l,/dtyp))[0]
	z = pix*(n - ns)/wdist
	alp = talp
	tbet = tbet + atan(z)
	bet = (dth = fltarr(siz[[1,2]]))
	for i = 0l, siz[1] - 1 do begin
		bet[i,*] = tbet
		dth[i,*] = tdth[i]
	endfor

	if keyword_set(ang) then begin
		qxy = !radeg*dth
		qz = !radeg*bet
		znam = 'Beta'
	endif else begin
		k = 2*!pi/lam
		apb = (alp + bet)/2
		amb = (alp - bet)/2
		qxy = 2*k*sqrt((sin(apb)*sin(amb))^2 + cos(alp)*cos(bet)*sin(dth/2)^2)
		if keyword_set(sgn) then qxy = qxy*Sign(dth)
		qz = 2*k*sin(apb)*cos(amb)
		znam = 'Q_z'
	endelse

	if siz[1] gt 1 then begin
		if keyword_set(rel) then tight = 0 else tight = 1
		tdat = Img_trig(pdat[*,*,0],qxy,qz,xtr=tqxy,ytr=tqz,min=tight)
		edat = Img_trig(pdat[*,*,1],/last)
		res = fltarr(4,siz[1],siz[2])
		for i = 0l, siz[1] - 1 do begin
			res[0,i,*] = tqxy[i]
			res[1,i,*] = tqz
		endfor
		res[2,*,*] = tdat
		res[3,*,*] = edat

		if keyword_set(vrb) and n_elements(wptr) ne 0 then begin
			tem = res[1,0,*]
			vran = [res[1,0,wptr[0]],max(tem)]
			if n_elements(wptr) eq 2 then vran[1] = res[1,0,wptr[1]]
			pvran = strjoin(string(vran,form='(f6.3)'),',')
			print
			print, 'Patching for ' + znam + ' = [' + pvran + ']'
		endif
	endif else begin
		res = fltarr(3,siz[2])
		if horfl then res[0,*] = qxy else res[0,*] = qz
		res[1,*] = pdat[0,*,0]
		res[2,*] = pdat[0,*,1]
	endelse

	return, res
end