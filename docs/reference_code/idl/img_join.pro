Function Img_join, id_0, id_1, id_2, id_3, id_4, id_5, id_6, id_7, $
	horizontal= hor, vertical= ver, boundary = bnd, factor = mfac, _extra = _e

;+
; NAME:
;		IMG_JOIN
; VERSION:
;		7.0
; PURPOSE:
;		Joins 2D image data, matching amplitudes in the overlap areas.
; CATEGORY:
;		2D data processing.
; CALLING SEQUENCE:
;		Result = IMG_JOIN(ID_0, ...  [, keywords])
; INPUTS:
;	ID_0, ID_1, .. ID_7
;		2D image data sets.  Each input must be either a [3,M,N] array or a
;		[4,M,N] array, where the first "slice", [0,*,*], represents the X
;		coordinates of the data, the second slice represents the Y coordinates,
;		the third slice is the data itself and the fourth slice (if present)
;		represents the data errors.  Mixing of the two types of inputs is not
;		allowed.  The maximal number of data sets accepted is 8 (can be
;		increased in the future if needed.
; OPTIONAL INPUT PARAMETERS:
;		None.
; KEYWORD PARAMETERS:
;	/HORIZONTAL											|	One and only one of
;		Switch.  If set, the images are patched in the	|	these two may be
;		horizontal (X) direction.						|	given.  If none is,
;	/VERTICAL											|	the default option
;		Switch.  If set, the images are patched in the	|	is "horizontal".
;		vertical (Y) direction.							|
;	/BOUNDARY
;		Switch.  If set, higher order calculation of shape boundary values (see
;		the IDL fuctions TRIANGULATE and TRIGRID for details) is performed.
;		This is rarely needed and the exexution time penalty is heavy (up to
;		factor 3) so it should be used only when necessary.
;	/NO_FERR
;		Switch.  If set, fitting errors are ignored in the matching.
;	FACTOR
;		Optional output, see below.
;	_EXTRA
;		A formal key, used to transfer additional keywords to SCAN_JOIN and
;		routines imbedded therein.  Especially, the SCAN_JOIN keywords /FORCE
;		and /RELAXED can be used.
; OUTPUTS:
;		Returns an output of the same format as the inputs (see above), covering
;		the largest rectangle overlapped by all the input data sets.
; OPTIONAL OUTPUT PARAMETERS:
;	FACTOR
;		A vector of length N (the number of scans present) returning the
;		multiplicative factors of the matches.  The i-th value is the factor by
;		which scan #i is multiplied, relative to scan #0.  The 0-th value is
;		always 1.
; COMMON BLOCKS:
;		None.
; SIDE EFFECTS:
;		None.
; RESTRICTIONS:
;		1)  Each data set must have some overlap with the next one, unless
;			/FORCE is set.
;		2)	All data sets must have a non-null common transverse area, meaning,
;			in case of horizontal patching, a common Y-range, and in case of
;			vertical patching, a common X-range.
; PROCEDURE:
;		Amplitude matching over overlap areas, using interpolation to generate
;		comparable sets.  Also using interpolation to assure a rectangular
;		coordinate grid for the final result.
;		Calls IMG_TRIG, SCAN_JOIN and SCAN_ORDER.  Calls FPU_FIX, MAKE_GRID,
;		NPARDEF, ONE_OF and TOLER from MIDL.
; MODIFICATION HISTORY:
;		Created  1-APR-2008 by Mati Meron.
;-

	on_error, 1

	nmax = 8
	del = Toler()
	eps = (machar()).xmin
	vfl = One_of(hor,ver) > 0

	n = Npardef(id_0, id_1, id_2, id_3, id_4, id_5, id_6, id_7, whi=j)
	if n gt 0 then begin
		idnam = strcompress('id_' + sindgen(nmax),/remove)
		wdnam = strcompress('wd_' + sindgen(n),/remove)
		odnam = strcompress('od_' + sindgen(n),/remove)
		dims = (udims = lonarr(3,n))
		lims = fltarr(2,n)
		mfac = replicate(1.,n)

		for i = 0, n-1 do begin
			dum = execute('tem = size(' + idnam[j[i]] +')')
			if tem[0] eq 3 then dims[*,i] = tem[1:3] $
			else message, 'Input # ' + string(j[i],form='(i0)') + ' is bad!'
		endfor

		pmin = min(dims[0,*],max=pmax)
		if pmin eq pmax then begin
			case (pmin < 4) of
				3	:	erfl = 0
				4	:	erfl = 1
				else:	message, 'Bad data format!'
			endcase
		endif else message, 'Inconsistent data format!'

		for i = 0, n-1 do begin
			dum = execute('tem = ' + idnam[j[i]])
			cmin = min(tem[1-vfl,*,*],max=cmax)
			lims[*,i] = [cmin,cmax]
		endfor
		glims = [max(lims[0,*]),min(lims[1,*])]
		if glims[0] ge glims[1] then message, 'Unpatchable data!'

		if vfl then begin
			for i = 0, n-1 do begin
				dum = execute('tem = ' + idnam[j[i]])
				x = reform(tem[0,*,0])
				ran = where(x ge glims[0] and x le glims[1], nran)
				tem = tem[*,ran,*]
				ttem = fltarr(3,dims[2,i])
				ttem[0,*] = reform(tem[1,0,*])
				ttem[1,*] = total(reform(tem[2,*,*]),1)
				if erfl then ttem[2,*] = sqrt(total(reform(tem[3,*,*]^2),1)) $
				else ttem[2,*] = sqrt(ttem[1,*])
				udims[*,i] = (size(tem))[1:3]
				dum = execute(wdnam[i] + ' = tem')
				dum = execute(odnam[i] + ' = ttem')
			endfor

			if min(udims[1,*],max=umax) ne umax then begin
				xx = Make_grid(glims,umax)
				for i = 0, n-1 do begin
					if udims[1,i] lt umax then begin
						dum = execute('tem = ' + wdnam[i])
						tx = reform(tem[0,*,*])
						ty = reform(tem[1,*,*])
						yy = reform(ty[0,*])
						ttem = fltarr(3+erfl,umax,udims[2,i])
						for l = 0l, umax-1 do begin
							ttem[0,l,*] = xx[l]
							ttem[1,l,*] = yy
						endfor
						triangulate, tx, ty, tring, bound
						if keyword_set(bnd) then begin
							ttem[2,*,*] = trigrid(tx,ty,$
							reform(tem[2,*,*]),tring,ext=bound,xout=xx,yout=yy)
							if erfl then ttem[3,*,*] = trigrid(tx,ty,$
							reform(tem[3,*,*]),tring,ext=bound,xout=xx,yout=yy)
						endif else begin
							ttem[2,*,*] = trigrid(tx,ty,$
							reform(tem[2,*,*]),tring,xout=xx,yout=yy)
							if erfl then ttem[3,*,*] = trigrid(tx,ty,$
							reform(tem[3,*,*]),tring,xout=xx,yout=yy)
						endelse
						dum = execute(wdnam[i] + ' = ttem')
					endif
				endfor
			endif

			dum = execute('k = Scan_order(' + strjoin(odnam,',') + ')')
			dum = execute('res = ' + wdnam[k[0]])
			dum = execute('pres = ' + odnam[k[0]])
			for i = 1, n-1 do begin
				fir = res
				dum = execute('sec = ' + wdnam[k[i]])
				lo = pres
				dum = execute('hi = ' + odnam[k[i]])
				nlo = (size(lo))[2]
				nhi = (size(hi))[2]
				pres = Scan_join(lo,hi,fac=ffac,efac=efac,over=ovlo,_extra=_e)
				mfac[i] = ffac[1]
				ntot = (size(pres))[2]
				ovhi = nlo + nhi - ntot
				if erfl then sec[3,*,*] = $
					sqrt((efac[1]*sec[2,*,*])^2 + (ffac[1]*sec[3,*,*])^2)
				sec[2,*,*] = ffac[1]*sec[2,*,*]
				md = (lmd = fir[*,*,nlo-ovlo[1]:nlo-1])
				if erfl then alp = 1/(md[3,*,*]^2 > eps) $
				else alp = 1/(abs(md[2,*,*]) > eps)
				xx = reform(md[0,*,0])
				yy = reform(md[1,0,*])
				tem = sec[*,*,0:(ovhi < (nhi-1))]
				tx = reform(tem[0,*,*])
				ty = reform(tem[1,*,*])
				triangulate, tx, ty, tring
				md[2,*,*] = trigrid(tx,ty,reform(tem[2,*,*]),$
				tring,xout=xx,yout=yy)
				if erfl then begin
					md[3,*,*] = trigrid(tx,ty,reform(tem[3,*,*]),$
					tring,xout=xx,yout=yy)
					bet = 1/(md[3,*,*]^2 > eps)
				endif else bet = 1/(abs(md[2,*,*]) > eps)
				fir[2,*,nlo-ovlo[1]:nlo-1] = $
				(alp*lmd[2,*,*] + bet*md[2,*,*])/(alp + bet)
				if erfl then fir[3,*,nlo-ovlo[1]:nlo-1] = sqrt(1/(alp + bet))
				if ntot gt nlo then begin
					res = fltarr(3+erfl,umax,ntot)
					res[*,*,0:nlo-1] = fir
					res[*,*,nlo:ntot-1] = sec[*,*,ovhi:nhi-1]
					res[2,*,*]= Img_trig(reform(res[2,*,*]),res[0:1,*,*],ytr=yy)
					if erfl then res[3,*,*] = Img_trig(reform(res[2,*,*]),/last)
					for l = 0l, umax-1 do res[1,l,*] = yy
				endif else res = fir
			endfor
		endif else begin
			for i = 0, n-1 do begin
				dum = execute('tem = ' + idnam[j[i]])
				y = reform(tem[1,0,*])
				ran = where(y ge glims[0] and y le glims[1], nran)
				tem = tem[*,*,ran]
				ttem = fltarr(3,dims[1,i])
				ttem[0,*] = reform(tem[0,*,0])
				ttem[1,*] = total(reform(tem[2,*,*]),2)
				if erfl then ttem[2,*] = sqrt(total(reform(tem[3,*,*]^2),2)) $
				else ttem[2,*] = sqrt(ttem[1,*])
				udims[*,i] = (size(tem))[1:3]
				dum = execute(wdnam[i] + ' = tem')
				dum = execute(odnam[i] + ' = ttem')
			endfor

			if min(udims[2,*],max=umax) ne umax then begin
				yy = Make_grid(glims,umax)
				for i = 0, n-1 do begin
					if udims[2,i] lt umax then begin
						dum = execute('tem = ' + wdnam[i])
						tx = reform(tem[0,*,*])
						ty = reform(tem[1,*,*])
						xx = reform(tx[*,0])
						ttem = fltarr(3+erfl,udims[1,i],umax)
						for l = 0l, umax-1 do begin
							ttem[0,*,l] = xx
							ttem[1,*,l] = yy[l]
						endfor
						triangulate, tx, ty, tring, bound
						if keyword_set(bnd) then begin
							ttem[2,*,*] = trigrid(tx,ty,$
							reform(tem[2,*,*]),tring,ext=bound,xout=xx,yout=yy)
							if erfl then ttem[3,*,*] = trigrid(tx,ty,$
							reform(tem[3,*,*]),tring,ext=bound,xout=xx,yout=yy)
						endif else begin
							ttem[2,*,*] = trigrid(tx,ty,$
							reform(tem[2,*,*]),tring,xout=xx,yout=yy)
							if erfl then ttem[3,*,*] = trigrid(tx,ty,$
							reform(tem[3,*,*]),tring,xout=xx,yout=yy)
						endelse
						dum = execute(wdnam[i] + ' = ttem')
					endif
				endfor
			endif

			dum = execute('k = Scan_order(' + strjoin(odnam,',') + ')')
			dum = execute('res = ' + wdnam[k[0]])
			dum = execute('pres = ' + odnam[k[0]])
			for i = 1, n-1 do begin
				fir = res
				dum = execute('sec = ' + wdnam[k[i]])
				lo = pres
				dum = execute('hi = ' + odnam[k[i]])
				nlo = (size(lo))[2]
				nhi = (size(hi))[2]
				pres = Scan_join(lo,hi,fac=ffac,efac=efac,over=ovlo,_extra=_e)
				mfac[i] = ffac[1]
				ntot = (size(pres))[2]
				ovhi = nlo + nhi - ntot
				if erfl then sec[3,*,*] = $
					sqrt((efac[1]*sec[2,*,*])^2 + (ffac[1]*sec[3,*,*])^2)
				sec[2,*,*] = ffac[1]*sec[2,*,*]
				md = (lmd = fir[*,nlo-ovlo[1]:nlo-1,*])
				if erfl then alp = 1/(md[3,*,*]^2 > eps) $
				else alp = 1/(abs(md[2,*,*]) > eps)
				xx = reform(md[0,*,0])
				yy = reform(md[1,0,*])
				tem = sec[*,0:(ovhi < (nhi-1)),*]
				tx = reform(tem[0,*,*])
				ty = reform(tem[1,*,*])
				triangulate, tx, ty, tring
				md[2,*,*] = trigrid(tx,ty,reform(tem[2,*,*]),$
				tring,xout=xx,yout=yy)
				if erfl then begin
					md[3,*,*] = trigrid(tx,ty,reform(tem[3,*,*]),$
					tring,xout=xx,yout=yy)
					bet = 1/(md[3,*,*]^2 > eps)
				endif else bet = 1/(abs(md[2,*,*]) > eps)
				fir[2,nlo-ovlo[1]:nlo-1,*] = $
				(alp*lmd[2,*,*] + bet*md[2,*,*])/(alp + bet)
				if erfl then fir[3,nlo-ovlo[1]:nlo-1,*] = sqrt(1/(alp + bet))
				if ntot gt nlo then begin
					res = fltarr(3+erfl,ntot,umax)
					res[*,0:nlo-1,*] = fir
					res[*,nlo:ntot-1,*] = sec[*,ovhi:nhi-1,*]
					res[2,*,*]= Img_trig(reform(res[2,*,*]),res[0:1,*,*],xtr=xx)
					if erfl then res[3,*,*] = Img_trig(reform(res[2,*,*]),/last)
					for l = 0l, umax-1 do res[0,*,l] = xx
				endif else res = fir
			endfor
		endelse
	endif else message, 'Missing Data!

	return, FPU_fix(res)
end