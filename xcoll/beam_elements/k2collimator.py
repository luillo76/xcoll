import numpy as np
from .k2.materials import Material, Crystal
from .collimators import BaseCollimator

class K2Engine:

    def __init__(self, n_alloc, random_generator_seed=None):

        self._n_alloc = n_alloc

        if random_generator_seed is None:
            self.random_generator_seed = np.random.randint(1, 100000)
        else:
            self.random_generator_seed = random_generator_seed

        try:
            import xcoll.beam_elements.pyk2 as pyk2
        except ImportError:
            print("Warning: Failed importing pyK2 (did you compile?). " \
                  + "K2collimators will be installed but are not trackable.")
        else:
            pyk2.pyk2_init(n_alloc=n_alloc, random_generator_seed=self.random_generator_seed)

    @property
    def n_alloc(self):
        return self._n_alloc


class K2Collimator(BaseCollimator):

    iscollective = True

    def __init__(self, **kwargs):
        self._k2engine = kwargs.pop('k2engine')
        self.onesided = kwargs.pop('onesided', False)
        self.dpx = kwargs.pop('dpx', 0)
        self.dpy = kwargs.pop('dpy', 0)
        self.offset = kwargs.pop('offset', 0)
        tilt = kwargs.pop('tilt', [0,0])
        if hasattr(tilt, '__iter__'):
            if isinstance(tilt, str):
                raise ValueError("Variable tilt has to be a number or array of numbers!")
            elif len(tilt) == 1:
                tilt = [tilt[0], tilt[0]]
        else:
            tilt = [tilt, tilt]
        self.tilt = np.array(tilt, dtype=np.float64)
        self.material = kwargs.pop('material', None)
        self._reset_random_seed = False
        super().__init__(**kwargs)

    @property
    def material(self):
        return self._material

    @material.setter
    def material(self, material):
        if material is not None and not isinstance(material, Material):
            raise ValueError(f"The material {material} is not a valid xcoll.Material!")
        self._material = material

    @property
    def k2engine(self):
        return self._k2engine

    def reset_random_seed(self):
        self._reset_random_seed = True

    def track(self, particles):  # TODO: write impacts
        npart = particles._num_active_particles
        if npart > self.k2engine.n_alloc:
            raise ValueError(f"Tracking {npart} particles but only {self.k2engine.n_alloc} allocated!")
        if npart == 0:
            return
        if self._reset_random_seed == True:
            reset_seed = self.k2engine.random_generator_seed
            self._reset_random_seed = False
        else:
            reset_seed = -1
        if self.material is None:
            raise ValueError("Cannot track if material is not set!")
        
        # TODO: when in C, drifting should call routine from drift element
        #       such that can be exact etc
        if not self.is_active:
            # Drift full length
            L = self.length
            if L > 0:
                rpp = particles.rpp[:npart]
                xp = particles.px[:npart] * rpp
                yp = particles.py[:npart] * rpp
                dzeta = particles.rvv[:npart] - ( 1 + ( xp*xp + yp*yp ) / 2 )
                particles.x[:npart] += xp * L
                particles.y[:npart] += yp * L
                particles.s[:npart] += L
                particles.zeta[:npart] += dzeta*L
        else:
            # Drift inactive front
            L = self.inactive_front
            if L > 0:
                rpp = particles.rpp[:npart]
                xp = particles.px[:npart] * rpp
                yp = particles.py[:npart] * rpp
                dzeta = particles.rvv[:npart] - ( 1 + ( xp*xp + yp*yp ) / 2 )
                particles.x[:npart] += xp * L
                particles.y[:npart] += yp * L
                particles.s[:npart] += L
                particles.zeta[:npart] += dzeta*L

            from .k2 import track
            track(self, particles, npart, reset_seed)

            # Drift inactive back
            L = self.inactive_back
            if L > 0:
                rpp = particles.rpp[:npart]
                xp = particles.px[:npart] * rpp
                yp = particles.py[:npart] * rpp
                dzeta = particles.rvv[:npart] - ( 1 + ( xp*xp + yp*yp ) / 2 )
                particles.x[:npart] += xp * L
                particles.y[:npart] += yp * L
                particles.s[:npart] += L
                particles.zeta[:npart] += dzeta*L

            particles.reorganize()
        
    def to_dict(self):
        # TODO how to save ref to impacts?
        thisdict = {}
        thisdict['__class__'] = 'K2Collimator'
        thisdict['n_alloc'] = self._k2engine.n_alloc
        thisdict['random_generator_seed'] = self._k2engine.random_generator_seed
        thisdict['active_length'] = self.active_length
        thisdict['inactive_front'] = self.inactive_front
        thisdict['inactive_back'] = self.inactive_back
        thisdict['angle'] = self.angle
        thisdict['jaw_F_L'] = self.jaw_F_L
        thisdict['jaw_F_R'] = self.jaw_F_R
        thisdict['jaw_B_L'] = self.jaw_B_L
        thisdict['jaw_B_R'] = self.jaw_B_R
        thisdict['onesided'] = 1 if self.onesided else 0
        thisdict['dx'] = self.dx
        thisdict['dy'] = self.dy
        thisdict['dpx'] = self.dpx
        thisdict['dpy'] = self.dpy
        thisdict['offset'] = self.offset
        thisdict['tilt'] = self.tilt
        thisdict['is_active'] = 1 if self.is_active else 0
        thisdict['material'] = self.material.to_dict()
        return thisdict


    @classmethod
    def from_dict(cls, thisdict, *, engine=None):
         # TODO how to get ref to impacts?
        if engine is None:
            print("Warning: no engine given! Creating a new one...")
            engine = K2Engine(thisdict['n_alloc'], thisdict['random_generator_seed'])
        else:
            if engine.n_alloc != thisdict['n_alloc']:
                raise ValueError("The provided engine is incompatible with the engine of the "\
                                 "stored element: n_alloc is different.")
            if engine.random_generator_seed != thisdict['random_generator_seed']:
                raise ValueError("The provided engine is incompatible with the engine of the "\
                                 "stored element: random_generator_seed is different.")
        return cls(
            k2engine = engine,
            active_length = thisdict['active_length'],
            inactive_front = thisdict['inactive_front'],
            inactive_back = thisdict['inactive_back'],
            angle = thisdict['angle'],
            jaw_F_L = thisdict['jaw_F_L'],
            jaw_F_R = thisdict['jaw_F_R'],
            jaw_B_L = thisdict['jaw_B_L'],
            jaw_B_R = thisdict['jaw_B_R'],
            onesided = True if thisdict['onesided']==1 else False,
            dx = thisdict['dx'],
            dy = thisdict['dy'],
            dpx = thisdict['dpx'],
            dpy = thisdict['dpy'],
            offset = thisdict['offset'],
            tilt = thisdict['tilt'],
            is_active = True if thisdict['is_active']==1 else False,
            material = Material.from_dict(thisdict['material'])
        )
            
