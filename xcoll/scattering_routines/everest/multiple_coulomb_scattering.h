// copyright ############################### #
// This file is part of the Xcoll Package.   #
// Copyright (c) CERN, 2024.                 #
// ######################################### #

#ifndef XCOLL_EVEREST_MCS_H
#define XCOLL_EVEREST_MCS_H
#include <math.h>
#include <stdio.h>


/*gpufun*/
double iterat(double a, double b, double dh, double s) {
    double ds = s;
    while (1) {
        ds = ds*0.5;
        if (pow(s,3) < pow((a+b*s),2)) {
            s = s+ds;
        } else {
            s = s-ds;
        }
        if (ds < dh) {
            break;
        } else {
            continue;
        }
    }
    return s;
}


/*gpufun*/
double soln3(double a, double b, double dh, double smax) {
    double s;
    if (b == 0) {
        s = pow(a,0.6666666666666667);
        if (s > smax) {
            s = smax;
        }
        return s;
    }
    if (a == 0) {    
        if (b > 0) {
            s = pow(b,2);
        } else {
            s = 0;
        }
        if (s > smax) {
            s = smax;
        }
        return s;
    }
    if (b > 0) {
        if (pow(smax,3) <= pow((a + b*smax),2)) {
            s = smax;
            return s;
        } else {
            s = smax*0.5;
            s = iterat(a,b,dh,s);
        }
    } else {
        double c = (-1*a)/b;
        if (smax < c) {
            if ((pow(smax,3)) <= pow((a + b*smax),2)) {
                s = smax;
                return s;
            } else {
                s = smax*0.5;
                s = iterat(a,b,dh,s);
            }
        } else {
            s = c*0.5;
            s = iterat(a,b,dh,s);
        }
    }
    return s;
}


/*gpufun*/
double* scamcs(LocalParticle* part, double x0, double xp0, double s) {
    double* result = (double*)malloc(2 * sizeof(double));
    
    // Generate two Gaussian random numbers z1 and z2
    double r2 = 0;
    double v1 = 0;
    double v2 = 0;
    while (1) {
        v1 = 2*RandomUniform_generate(part) - 1;
        v2 = 2*RandomUniform_generate(part) - 1;
        r2 = pow(v1,2) + pow(v2,2);
        if(r2 < 1) {
            break;
        }
    }
    double a   = sqrt((-2*log(r2))/r2);
    double z1  = v1*a;
    double z2  = v2*a;

    // MCS scaling by length in units of radiation length
    double ss  = sqrt(s) * (1 + 0.038*log(s));

    result[0] = x0  + s*(xp0 + 0.5*ss*(z2 + z1*0.577350269));
    result[1] = xp0 + ss*z2;
    return result;
}


/*gpufun*/
double* mcs(EverestData restrict everest, LocalParticle* part, double zlm1, double p, double x, double xp, double z, double zp, int edge_check) {

    double const radl = everest->coll->radl;
    double s;
    double theta = 13.6e-3/p;
    double h   = 0.001;
    double dh  = 0.0001;
    double bn0 = 0.4330127019;
    double rlen0 = zlm1/radl;
    double rlen  = rlen0;
    double* result = (double*)malloc(5 * sizeof(double));

    x  = (x/theta)/radl;
    xp = xp/theta;
    z  = (z/theta)/radl;
    zp = zp/theta;

    if (edge_check){
        while (1) {
            double ae = bn0 * x;
            double be = bn0 * xp;
            // #######################################
            // ae = np.array(ae, dtype=np.double64)
            // be = np.array(be, dtype=np.double64)
            // dh = np.array(dh, dtype=np.double64)
            // rlen = np.array(rlen, dtype=np.double64)
            // s = np.array(s, dtype=np.double64)
            // #######################################
            s = soln3(ae,be,dh,rlen);
            if (s < h) {
                s = h;
            }
            // TODO: should cap s whenever we are out (the two if cases below), because now the scamcs is applied over an s that might be (slightly) too long
            double* res = scamcs(part, x, xp, s);
            x  = res[0];
            xp = res[1];
            free(res);
            if (x <= 0) {
                s = rlen0 - rlen + s;
                break; // go to 20
            }
            if (s + dh >= rlen) {
                s = rlen0;
                break; // go to 20
            }
            // go to 10
            rlen = rlen - s;
        }

    } else {
        double* res = scamcs(part, x, xp, rlen0);
        x  = res[0];
        xp = res[1];
        free(res);
        s = rlen0;
    }

    double* res = scamcs(part, z, zp, s);
    z  = res[0];
    zp = res[1];
    free(res);

    result[0] = s*radl;
    result[1] = (x*theta)*radl;
    result[2] = xp*theta;
    result[3] = (z*theta)*radl;
    result[4] = zp*theta;
    return result;
}

#endif /* XCOLL_EVEREST_MCS_H */