function [v] = positioning(v,f)
Shape = v;

%Translates to origin
CentOffset(1,:) = max(Shape);
CentOffset(2,:) = min(Shape);
CentOffset(3,:) = mean(CentOffset(1:2,:));
for i = 1:size(Shape,1)
    Shape(i,:) = Shape(i,:) - CentOffset(3,:);
end
clear CentOffset

Wait1 = waitbar(0/2,'Rotaiting...');
%Positiones according to normals distribution (UZY)

[v2, RUzy] = UzyPosCm_for_GUI(f,v);

%Positions the object to planform view by finding the rotation angles about
%the X and Y axes that provide the maximum surface area of the outline

RotStruct(1).v = v2;
[K, A] = boundary(v2(:,1),v2(:,2));
Area(1,1) = A;
clearvars K A

v2 = ([1, 0, 0; 0, cos(deg2rad(90)), -sin(deg2rad(90)); 0, sin(deg2rad(90)), cos(deg2rad(90))] *...
    v2')';
RotStruct(2).v = v2;
[K, A] = boundary(v2(:,1),v2(:,2));
Area(2,1) = A;
clearvars K A

v2 = ([cos(deg2rad(90)), 0, sin(deg2rad(90)); 0, 1, 0; -sin(deg2rad(90)), 0, cos(deg2rad(90))] *...
    v2')';
RotStruct(3).v = v2;
[K, A] = boundary(v2(:,1),v2(:,2));
Area(3,1) = A;
clearvars K A

Shape = RotStruct(find(Area(:) == max(Area))).v;

%Translates to origin
CentOffset(1,:) = max(Shape);
CentOffset(2,:) = min(Shape);
CentOffset(3,:) = mean(CentOffset(1:2,:));
for i = 1:size(Shape,1)
    Shape(i,:) = Shape(i,:) - CentOffset(3,:);
end
clear CentOffset

waitbar(1/2,Wait1);


% MaxAreaX = 0;
% MaxAreaY = 0;
% 
% %Find rotation angle about X axis
% for i = 1:360
%     angX = deg2rad(i);
%     Rx = [1, 0, 0; 0, cos(angX), -sin(angX); 0, sin(angX), cos(angX)];
%     ShapeTmpX = Shape';
%     ShapeTmpX = (Rx*ShapeTmpX)';
%     [K, AreaX] = convhull(ShapeTmpX(:,1),ShapeTmpX(:,2));
%     if AreaX > MaxAreaX
%         MaxAreaX = AreaX;
%         XRotAng = i;
%     end
%     
% end
% 
% %Rotate Accordingly
% clear AreaX K ShapeTmpX MaxAreaX
% angX = deg2rad(XRotAng);
% Rx = [1, 0, 0; 0, cos(angX), -sin(angX); 0, sin(angX), cos(angX)];
% Shape = (Rx*Shape')';
% clear angX Rx
% 
% waitbar(1/3,Wait1);
% 
% %Find rotation angle about X axis
% for i=1:360
%     angY = deg2rad(i);
%     Ry = [cos(angY), 0, sin(angY); 0, 1, 0; -sin(angY), 0, cos(angY)];
%     ShapeTmpY = Shape';
%     ShapeTmpY = (Ry*ShapeTmpY)';
%     [K, AreaY] = convhull(ShapeTmpY(:,1),ShapeTmpY(:,2));
%     if AreaY > MaxAreaY
%         MaxAreaY = AreaY;
%         YRotAng = i;
%     end
%     
% end
% 
% %Rotate Accordingly
% clear AreaY K ShapeTmpY MaxAreaY
% angY = deg2rad(YRotAng);
% Ry = [cos(angY), 0, sin(angY); 0, 1, 0; -sin(angY), 0, cos(angY)];
% Shape = (Ry*Shape')';
% clear angY Ry
% 
% waitbar(2/3,Wait1);

%plot
K = boundary(Shape(:,1),Shape(:,2));
%plot(Shape(K,1),Shape(K,2));
%XRotAng
%YRotAng
%Area



%Find Symmetry Rotation about Z
ang = Find_Mirror_Sym(Shape(K,1),Shape(K,2));

angZ = deg2rad(ang);
Rz = [cos(angZ), -sin(angZ), 0; sin(angZ), cos(angZ), 0; 0, 0, 1];
Shape = (Rz*Shape')';

v = Shape;

close(Wait1);
end


