## GID
## Keep monc gain to 500 nA/V in the macro
## compiling SURF>qdo do_files/dppc_gid.do
## execute   SURF>dppc_gid

######### Macro for GID scans 

def dppc_gid '
######Setup GID Slits
absclose
umv dth 14
gid_slits_16

###dth scan do not need sleep
_sleep=0

###GID scans for lower Qz
umv dth 14
umi 0.0904 0.0904
umv mabs 12
ascan dth 14 18 40 7

###GID scans for higher Qz
umvr sx -2
umv dth 14
umi 0.0904 6.5
ascan dth 14 18 40 7

###Cleanup
cleanup_sh
'
