Function Scan_PD_read, snum, fnum, filename = fnam, $
	orientation = ori, hroi = hroi, vroi = vroi, bad = bad, norm = nrm, $
	raw= raw, angles= ang, tilt= til, pinhole= pnh, relaxed= rel, nointer= nin,$
	jimg = jmg, title= rnam, _extra= _e

;+
; NAME:
;		SCAN_PD_READ
; VERSION:
;		7.0
; PURPOSE:
;		Reads a Pilatus Detector file.
; CATEGORY:
;		SPEC Input/Output.
; CALLING SEQUENCE:
;		Result = SCAN_PD_READ( SNUM [, FNUM] [, keywords])
; INPUTS:
;	SNUM
;		Single scan number.
;		Note 1:	unlike most other SCAN routines, SCAN_PD_READ
;				does not accept multiple scan numbers.
;		Note 2:	SNUM is mandatory when reading from a SPEC file, but not to be
;				used when reading the TIFF file directly.
; OPTIONAL INPUT PARAMETERS:
;	FNUM
;		Frame number within the scan.  If not given, defaults to 0.
; KEYWORD PARAMETERS:
;	FILENAME
;		Name of a TIFF file to be read directly (not using SPEC data).
;	ORIENTATION
;		Character input specifying the detector orientation.  Two possible
;		values, "HOR" (for horizontal) and "VER" (for vertical).  First letter
;		is sufficient.  Default is vertical.
;		Alternatively ORIENTATION can be provided as integer input, 0 for
;		horizontal, 1 for vertical.
;	HROI
;		Two element vector defining horizontal region of interest, in *pixels*.
;	VROI
;		Two element vector defining vertical region of interest, in *pixels*.
;	/BAD
;		Switch.  If set, faulty (very high count rate) pixels are removed from
;		the data.
;	/NORM
;		Switch.  If set, the data is normalized to monitor counts.
;	/RAW
;		Switch.  If set, the data is read "raw", meaning the X and Y
;		coordinates are expressed in pixels, not angles or Q-values.
;
;		Note:	When reading directly from a TIFF file, the data is always raw.
;				When reading through a SPEC file, the default coordinates are
;				Q_xy and Q_z.
;	/ANGLES
;		Switch.  If set the coordinates of the image are the angles DTHETA (for
;		horizontal) and BETA for vertical, instead of Q_xy and Q_z.
;
;		Note:	In case of direct read from TIFF file, /ANGLES has no effect.
;	TILT
;		Optional detector tilt angle (couterclockwise) in degrees.  Valid for
;		angle and Q-xy coordinates, has no effect if /RAW is set.
;	PINHOLE
;		Specifies that horizontal pinhole angle transformations are to be used.
;		If set or provided with any positive value, the distance PDSDIST from
;		the structure FILDAT (see common block) is used in the transformation.
;		If provided with any negative value, PDSTAT - PDSDIST is used (legacy
;		setting).  If not set, or provided with 0 value, pinhole transformation
;		is not applied.  If /RAW is set, PINHOLE has no effect.
;	/RELAXED
;		Switch.  If set, the internal transformation from angles to Q-values is
;		unconstrained.  By default it is constrained to the internal data
;		region, to avoid edge inaccuracies.
;	/NOINTER
;		Switch.  If set, data is not reinterpolated to a rectangular grid,
;		following a transformation to angles or q-values.  Default is to
;		reinterpolate.
;	/JIMG
;		Switch.  Specifies "just image" data readout, meaning raw data with no
;		coordinates and no transformations.
;	TITLE
;		Optional output, see below.
;	_EXTRA
;		A formal keyword, used to transfer additional keywords to embedded
;		routines.
; OUTPUTS:
;		Returns an array (type FLOAT) of dimension [4,PX,PY] where PX, PY are
;		the Pilatus horizontal (short) and vertical (long) pixel sizes (if
;		"HOR" orientation is used, the dimensions are reversed).  The [0,*,*]
;		and [1,*,*] pages of the array contain the X and Y coordinates (in pixel
;		angle or Q units).  The [2,*,*] page contains the data and the [3,*,*]
;		page contains the statistical errors.
;
;		Note:	If /JIMG is set, the output is a 2D array of dimension [PX,PY].
;		Note2:	PX, PY may be smaller than the above if HROI and/or VROI is used
; OPTIONAL OUTPUT PARAMETERS:
;	TITLE
;		Returns the Pilatus data filename to be used as a plot title, for the
;		use of calling routines.
; COMMON BLOCKS:
;		SPEC_FILE.  See the routine SPEC_FILE_INFO for description.
; SIDE EFFECTS:
;		None.
; RESTRICTIONS:
;		None other that the data files must exist.
; PROCEDURE:
;		Straightforward, reads the data using parameters stored in the FILDAT
;		structure in the common block.  Calls SCAN_COLUMN, SCAN_GET,
;		SCAN_PAR_READ, and SPEC_FILE_INFO.  Calls IMG_COO_CONV and IMG_TRIG.
;		Also calls DEFAULT, DEGLITCH, ISNUM, FILE_GET, STREQ, SIGN, STRMATCH_MM,
;		STRPARSE_MM, TYPE and WHERINSTRUCT, from MIDL.
; MODIFICATION HISTORY:
;		Created 15-AUG-2007 by Mati Meron.
;		Modified and documented 30-OCT-2007 by Mati Meron.
;		Modified 10-Nov-2007 by Mati Meron.  Internal changes.
;		Modified 15-NOV-2007 by Mati Meron.  Added keyword BAD.
;		Modified 25-MAR-2007 by Mati Meron.  Added keyword PINHOLE.
;		Modified 10-APR-2008 by Mati Meron.  Added keyword NOINTER and made
;		some internal changes.
;		Modified 15-APR-2008 by Mati Meron.  Added keyword JIMG.
;-

	common spec_file, exs, fildat, n_s, n_m, n_l, n_smax
	on_error, 1

	ext = '.tif'
	rotval = [0,1]
	if Isnum(ori) then ori = 0 > fix(ori) < 1 $
	else ori = Strmatch_mm(Default(ori,'',/dtyp),['hor','ver'],1,/nosub)
	profl = 0

	if n_params() gt 0 and Type(snum) gt 0 then begin
		Spec_file_info, _extra = _e
		dum = (Wherinstruct('new',_e))[0]
		if dum ge 0 then _e.(dum) = 0
		if (snum gt 0 and snum le fildat.nscan) then begin
			if fildat.status and fildat.pdfl then begin
				cur = fildat.scan[snum]
				if cur.pdstat then begin
					fnum = Default(fnum,0)
					dum = Strparse_mm(cur.pdfnam,'_',lis)
					ran = fix(lis[dum]) + [0,cur.ncr[1]-1]
					if (fnum ge ran[0] and fnum le ran[1]) then begin
						zlen = strlen(lis[dum])
						fcod = strcompress('(I0'+string(zlen)+')',/rem)
						lis[dum] = string(fnum,fcod)
						rnam = fildat.pdpath + strjoin(lis,'_') + ext
					endif else begin
						fran = strcompress(strjoin(string(ran),'-'),/rem)
						message, 'Frame number out of range, frames ' + $
						fran + ' are present!'
					endelse
					if ori lt 0 then ori = cur.pdhv
					if keyword_set(nrm) then begin
						ncol = ''
						if Type(nrm) eq 7 then ncol = nrm $
						else if nrm eq 1 then ncol = 'monc'
						if ncol ne '' then begin
							col = Scan_column(snum,ncol)
							nfac = Total(col)/(cur.ncr[1]*col[fnum-ran[0]])
						endif
					endif else nfac = 1.
					if not (keyword_set(raw) or keyword_set(jmg)) then profl = 1
				endif else message, 'No PD set or no PD data in this scan!'
			endif else message, 'No data or no PD data in the current file!'
		endif else message, 'Invalid scan number!
	endif else begin
		rnam = File_get(fnam,_extra=_e)
		ori = abs(ori)
		nfac = 1.
	endelse

	dat = rotate(read_tiff(rnam),rotval[ori])
	if keyword_set(bad) then dat = Deglitch(dat,3)
	dims = (size(dat))[1:2]
	if n_elements(hroi) eq 2 then begin
		whroi = 0 > hroi < (dims[0]-1)
		whroi = [min(whroi,max=max),max]
	endif else whroi = [0,dims[0]-1]
	if n_elements(vroi) eq 2 then begin
		wvroi = 0 > vroi < (dims[1]-1)
		wvroi = [min(wvroi,max=max),max]
	endif else wvroi = [0,dims[1]-1]
	dat = dat[whroi[0]:whroi[1],wvroi[0]:wvroi[1]]
	dims = (size(dat))[1:2]

	if not keyword_set(jmg) then begin
		res = fltarr([4,dims])
		tem = findgen(dims[1]) + wvroi[0]
		for i = 0l, dims[0] - 1 do begin
			res[0,i,*] = i + whroi[0]
			res[1,i,*] = tem
			endfor
		res[2,*,*] = dat
		res[3,*,*] = sqrt(dat)
		res[2:3,*,*] = nfac*res[2:3,*,*]
	endif else res = dat

	if profl then begin
		if ori then cent = [fildat.addim[1] - cur.pdyc, cur.pdxc] $
		else cent = [cur.pdxc,cur.pdyc]
		angs = Scan_par_read(snum,['In_Rot','Out_Rot','Det_Th'])
		dum = Scan_get(snum,head=head)
		if Streq(head[0],'Det_Th') then $
		angs[2] = (Scan_column(snum,0))[fnum-ran[0]]
		gl3 = (Scan_field_read(snum,'G_L'))[3]
		dist = cur.pdist + gl3*(1/cos(!dtor*angs[1]) - 1)
		case Sign(Default(pnh,0)) of
			-1	:	pdist = cur.pdist - cur.pdsdist
			0	:	pdist = 0.
			1	:	pdist = cur.pdsdist
		endcase
		qvl = 1 - keyword_set(ang)
		min = 1 - keyword_set(rel)
		coord = Img_coo_conv(res[0:1,*,*], dist= dist, pdist= pdist, $
			pix= fildat.adpix,cent=cent, alp=angs[0], bet=angs[1], dth=angs[2],$
			tau= til, lam= cur.lambda, /xrev, qvals= qvl, /sign, _extra= _e)
		if not keyword_set(nin) then begin
			rdat = Img_trig(reform(res[2,*,*]),coord,xtr=tqxy,ytr=tqz,min=min)
			edat = Img_trig(reform(res[3,*,*]),/last)
			for i = 0l, dims[0]-1 do begin
				res[0,i,*] = tqxy[i]
				res[1,i,*] = tqz
			endfor
			res[2,*,*] = rdat
			res[3,*,*] = edat
		endif else res[0:1,*,*] = coord
	endif

	return, res
end