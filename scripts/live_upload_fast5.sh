USER='d_nanopore'
SERVER='login-transfer.scicore.unibas.ch'
# without trailing slash, this will create a directory at destination
DEST='genome-assembly-pipeline/genome-assembly/runs/2022_01_14_Alex_Sequencing/input'
READS='/var/lib/minknow/data/2022_01_14_Alex_Sequencing/no_sample/20220114_1326_MN23519_FAL02190_89855126/fast5/'


while true;
do
   rsync -varu --include "*.fast5" --exclude "*" $READS $USER@$SERVER:$DEST
   sleep 300;
done

# rsync relevant options:
# -a : transfer in archive mode
# -v : verbose
# -r : recursive
# -u : update. Skips files that are newer on the receiver.
# -n : performs a dry run
# --ignore-existing : ignores files that already exist on the receiver
# --remove-source-files : sender removes synchronized files
