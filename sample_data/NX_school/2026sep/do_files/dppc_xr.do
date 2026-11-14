### File Name: dppc_xr
##compile SURF>qdo do_files/dppc_xr.do
##execute SURF>dppc_xr

def dppc_xr '

_sleep=3
umv mabs 52
ref_slits


#scan1
umk 0 0 0.016
umv mabs 41
lscan 0.0175 0.04 18 2

#scan2
umk 0 0 0.0325
umv mabs 31
lscan 0.035 0.1 26 2

#scan3
umk 0 0 0.085
s1v 0.05 0.05
umv mabs 24
lscan 0.09 0.19 20 2

#scan4
umk 0 0 0.16
s1v .1 .1
umv mabs 18
lscan 0.17 0.45 28 5

#End Scans
cleanup_sh
'
