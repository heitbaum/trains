
doFlatcar = true;
doContainer = false;

module __Customizer_Limit__ () {}

$fn=64;

len = 120;
top_cutout = 63;
end_cutout = ((len - top_cutout)/2)-2;
w=21;
ow=17.5;

cutout_h = 6.0;

if (doFlatcar)
    flatcar();
if (doContainer)
    container();

module container() {
    translate([0, -6, 13])
    rotate([180, 0, 0]) 
    {
        translate([-10, -3, 1]) {

            difference() {
                cube([len+20, w+6, 12]);
                translate([10-.5, 2, -2]) {
                    cube([len+1, w+2, 13]);
                }
                translate([2, 8.5, -2]) {
                    cube([len+16, 10, 13]);
                }
            }
        }
    }
}

module flatcar() {
    difference() {
        union() {
            translate([end_cutout, 0, 0])
                roundedBlock(len-(end_cutout*2), w, 12, 1);
            translate([0, (w-ow)/2, cutout_h])
                cube([len, ow, 3.01]);
            // truck mount
            translate([11, w/2, cutout_h-2.66])
                cylinder(d=5, h=2.66);
            translate([len-11, w/2, cutout_h-2.66])
                cylinder(d=5, h=2.66);
            // pin to stop truck from rotating
            translate([11+9, w/2, cutout_h-2.66])
                cylinder(d=2, h=2.66);
            translate([len-(11+9), w/2, cutout_h-2.66])
                cylinder(d=2, h=2.66);
        }
        // cut off rounded top
        translate([0, -.01, 9])
            cube([len, w+.02, 4]);
        // inner compartment
        translate([(len-top_cutout)/2, .75, 2])
            cube([top_cutout, w-1.5, 9]);

        // truck mounting holes
        translate([11, w/2, 0])
            cylinder(d=2.5, h=10);
        translate([len-11, w/2, 0])
            cylinder(d=2.5, h=10);

    }
}

//roundedBlock(w, w, 16, 3);

fn=16*1;

module roundedBlock(l, w, h, r)
{
    translate([r, r, r])
    hull() 
    {
        l1 = l - (r*2);
        w1 = w - (r*2);
        h1 = h - (r*2);
        translate([0, 0, 0])
            corner(h1, r);
        translate([0, w1, 0])
            corner(h1, r);
        translate([l1, 0, 0])
            corner(h1, r);
        translate([l1, w1, 0])
            corner(h1, r);
    }
}

module corner(h, r) {
    cylinder(r=r, h=h, $fn=fn);
    sphere(r=r, $fn=fn);
    translate([0, 0, h])
        sphere(r=r, $fn=fn);

}





