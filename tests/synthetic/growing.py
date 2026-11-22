"""A finished data set replayed into another folder as it was measured.

For the live-update tests (``tests/test_gui_live.py``, ``tests/test_live.py``,
``lss_core.live``): SPEC writes a scan's header, then one data line per
point, then comment lines; the Pilatus writes one image per point, which
can reach the disk after (or long after) its SPEC line; MCA files of
``getandsave_mca`` scans appear with their scan.

    g = Growing(synth.make_burn_dataset(src), dst, image_lag=2)
    g.advance(8)        # 8 data lines written, images of the first 6
    g.flush_images()    # the images that were late
    g.finish()          # everything; the copy is then byte-identical to the source

Any data set made by ``tests/synth.py`` or ``synthetic.xrr_images.render``
can be replayed. The SPEC text is rewritten whole at each step (what is on
disk is always a prefix of the source file); images and MCA files are
copied unchanged. Nothing is written into the source folder.
"""
import os
import re
import shutil


class Growing:
    def __init__(self, src_spec, dst_dir, image_lag=0, image_folder='pilatus', mca_folder='vortex'):
        self.src_spec = os.path.abspath(str(src_spec))
        self.name = os.path.basename(self.src_spec)
        self.src_dir = os.path.dirname(self.src_spec)
        self.dst_dir = os.path.abspath(str(dst_dir))
        self.spec = os.path.join(self.dst_dir, self.name)
        self.image_lag = image_lag
        self.folders = (image_folder, mca_folder)
        for f in self.folders:
            os.makedirs(os.path.join(self.dst_dir, f), exist_ok=True)
        self._events = self._parse(open(self.src_spec).read())
        self._pos = 0                  # events applied
        self._text = []
        self._pending = []             # (lines still to wait, image path)
        self.points = {}               # scan -> data lines written
        self.images = {}               # scan -> images written
        self._write()

    # ---- parsing ------------------------------------------------------------
    def _parse(self, text):
        """Events: ('text', chunk) for headers and comments, ('line', scan,
        point, text) for data lines. Images and MCA files are attached to
        their scan's lines and headers."""
        events, scan, point = [], None, 0
        pending = []
        for line in text.splitlines(True):
            m = re.match(r'#S\s+(\d+)', line)
            if m:
                scan, point = int(m.group(1)), 0
            if line.strip() and not line.startswith('#') and scan is not None:
                if pending:
                    events.append(('text', ''.join(pending), scan))
                    pending = []
                events.append(('line', scan, point, line))
                point += 1
            else:
                pending.append(line)
        if pending:
            events.append(('text', ''.join(pending), scan))
        return events

    def _image(self, scan, point):
        p = os.path.join(self.src_dir, self.folders[0], '%s_SCAN-%d_%04d.tif' % (self.name, scan, point))
        return p if os.path.exists(p) else None

    def _mca(self, scan):
        p = os.path.join(self.src_dir, self.folders[1], '%s_%d_mca' % (self.name, scan))
        return p if os.path.exists(p) else None

    # ---- writing --------------------------------------------------------------
    def _write(self):
        with open(self.spec, 'w') as f:
            f.write(''.join(self._text))

    def _copy(self, path, folder):
        shutil.copy2(path, os.path.join(self.dst_dir, folder, os.path.basename(path)))

    def _apply(self, ev):
        if ev[0] == 'text':
            self._text.append(ev[1])
            # a scan's MCA file comes with its header (getandsave_mca writes it whole)
            for scan in {int(s) for s in re.findall(r'^#S\s+(\d+)', ev[1], re.M)}:
                if self._mca(scan):
                    self._copy(self._mca(scan), self.folders[1])
            return False
        _, scan, point, line = ev
        self._text.append(line)
        self.points[scan] = self.points.get(scan, 0) + 1
        self._pending = [(n - 1, s, p) for n, s, p in self._pending]
        img = self._image(scan, point)
        if img is not None:
            self._pending.append((self.image_lag, scan, img))
        self._release(lambda n: n <= 0)
        return True

    def _release(self, ready):
        keep = []
        for n, scan, img in self._pending:
            if ready(n):
                self._copy(img, self.folders[0])
                self.images[scan] = self.images.get(scan, 0) + 1
            else:
                keep.append((n, scan, img))
        self._pending = keep

    def advance(self, lines=1):
        """Write the next ``lines`` data lines (and any header or comment
        text before them); images follow ``image_lag`` lines later. Returns
        the number of data lines written (fewer at the end of the file)."""
        done = 0
        while self._pos < len(self._events) and done < lines:
            if self._apply(self._events[self._pos]):
                done += 1
            self._pos += 1
        # text that closes the last scan written (comments, blank line) waits
        # for the next scan's first line, as on disk while SPEC is counting
        self._write()
        return done

    def advance_to(self, scan, points):
        """Write until ``scan`` has ``points`` data lines."""
        while self.points.get(scan, 0) < points and self._pos < len(self._events):
            self.advance(1)

    def flush_images(self):
        """Copy every image that is still late."""
        self._release(lambda n: True)

    def finish(self):
        """Write everything that is left; the copy then equals the source."""
        while self._pos < len(self._events):
            self._apply(self._events[self._pos])
            self._pos += 1
        self._write()
        self.flush_images()

    @property
    def done(self):
        return self._pos >= len(self._events) and not self._pending
